"""
TRILHA 1 — ANÁLISE DE PERFIL E CRÉDITO PROGRESSIVO
==================================================
O fluxo (módulo 4 do roteiro):
  1. eventos_comportamentais  → o que o cliente fez
  2. perfil_financeiro        → indicadores consolidados (renda, atrasos...)
  3. scores_credito           → nota de 0 a 1000 (com os MOTIVOS da nota)
  4. regras_progressao_credito→ quanto o limite pode subir
  5. limites_credito          → limite atual (+ historico_limite)

Transparência é um valor da Vértis: por isso o score guarda os fatores
positivos e negativos, e o app mostra ao cliente POR QUE a nota mudou.
"""
import json
from datetime import timedelta
from decimal import Decimal, ROUND_DOWN

import config
import relogio
from db import consultar, consultar_um, executar, inserir, auditar
from servicos import notificacoes

D = Decimal


def _arred(valor, passo=10) -> Decimal:
    """Arredonda para baixo em múltiplos de `passo` (ex.: 1.237 → 1.230)."""
    valor = D(str(valor))
    return (valor / passo).quantize(D("1"), rounding=ROUND_DOWN) * passo


# =====================================================================
# 1) LIMITE INICIAL — para quem não tem histórico nenhum
# =====================================================================
FATOR_RENDA = {"formal": D("0.20"), "informal": D("0.15"), "autonomo": D("0.15"),
               "beneficio": D("0.15"), "sem_renda": D("0")}


def limite_inicial(renda_declarada, tipo_renda) -> Decimal:
    """Começo pequeno e seguro: 15–20% da renda declarada, entre R$200 e R$1.000."""
    renda = D(str(renda_declarada or 0))
    valor = renda * FATOR_RENDA.get(tipo_renda or "sem_renda", D("0"))
    return _arred(min(max(valor, D(200)), D(1000)), 50)


# =====================================================================
# 2) PERFIL FINANCEIRO — consolida os indicadores
# =====================================================================
def atualizar_perfil(con, cliente_id: str) -> dict:
    agora = relogio.agora()
    d90, d30 = agora - timedelta(days=90), agora - timedelta(days=30)

    cliente = consultar_um(con, "SELECT renda_mensal_declarada FROM clientes WHERE id=%s", (cliente_id,))
    abertura = consultar_um(con, "SELECT MIN(aberta_em) AS aberta FROM contas WHERE cliente_id=%s", (cliente_id,))
    dias_conta = (agora - abertura["aberta"]).days if abertura and abertura["aberta"] else 0
    meses = max(0, dias_conta // 30)
    divisor = max(1, min(3, (dias_conta + 29) // 30))   # quantos meses existem para fazer média

    # --- renda comprovada: entradas reais na conta + renda recorrente do Open Finance
    entradas = consultar_um(con, """
        SELECT COALESCE(SUM(t.valor), 0) AS total
          FROM transacoes t JOIN contas c ON c.id = t.conta_id
         WHERE c.cliente_id = %s AND t.direcao = 'entrada' AND t.status = 'concluida'
           AND t.tipo IN ('pix_recebido', 'ted', 'deposito')
           AND t.realizada_em BETWEEN %s AND %s""", (cliente_id, d90, agora))["total"]
    externas = consultar_um(con, """
        SELECT COALESCE(SUM(te.valor), 0) AS total
          FROM transacoes_externas te
          JOIN contas_externas ce ON ce.id = te.conta_externa_id
          JOIN consentimentos_open_finance co ON co.id = ce.consentimento_id
         WHERE co.cliente_id = %s AND co.status = 'autorizado'
           AND te.direcao = 'entrada' AND te.eh_renda_recorrente = TRUE
           AND te.realizada_em >= %s""", (cliente_id, d90))["total"]
    renda = D(entradas) / divisor + D(externas) / 3

    # --- gasto médio: saídas da conta (menos o pagamento da fatura, para não contar 2x) + compras no crédito
    saidas = consultar_um(con, """
        SELECT COALESCE(SUM(t.valor), 0) AS total
          FROM transacoes t JOIN contas c ON c.id = t.conta_id
         WHERE c.cliente_id = %s AND t.direcao = 'saida' AND t.status = 'concluida'
           AND t.tipo <> 'pagamento_fatura' AND t.realizada_em BETWEEN %s AND %s""",
                         (cliente_id, d90, agora))["total"]
    compras = consultar_um(con, """
        SELECT COALESCE(SUM(cc.valor_total), 0) AS total
          FROM compras_cartao cc JOIN cartoes ca ON ca.id = cc.cartao_id
          JOIN contas c ON c.id = ca.conta_id
         WHERE c.cliente_id = %s AND cc.funcao_usada = 'credito' AND cc.status = 'autorizada'
           AND cc.realizada_em BETWEEN %s AND %s""", (cliente_id, d90, agora))["total"]
    gasto = (D(saidas) + D(compras)) / divisor

    # --- comprometimento: quanto da renda já está "preso" em dívidas
    parcelas = consultar_um(con, """
        SELECT COALESCE(SUM(p.valor_parcela), 0) AS total
          FROM contratos_emprestimo ct JOIN propostas_emprestimo p ON p.id = ct.proposta_id
         WHERE ct.cliente_id = %s AND ct.status IN ('ativo', 'em_atraso')""", (cliente_id,))["total"]
    lim = consultar_um(con, "SELECT limite_utilizado FROM limites_credito WHERE cliente_id=%s", (cliente_id,))
    divida_mensal = D(parcelas) + D(lim["limite_utilizado"] if lim else 0)
    renda_ref = renda if renda > 0 else D(str(cliente["renda_mensal_declarada"] or 0)) * D("0.5")
    if renda_ref > 0:
        comprometimento = min(divida_mensal / renda_ref * 100, D("999.99"))
    else:
        comprometimento = D(100) if divida_mensal > 0 else D(0)

    # --- histórico de pagamento das faturas
    fat = consultar_um(con, """
        SELECT SUM(status = 'paga' AND valor_total > 0 AND DATE(pago_em) <= data_vencimento) AS em_dia,
               SUM(dias_atraso > 0)          AS atrasadas,
               COALESCE(MAX(dias_atraso), 0) AS maior_atraso
          FROM faturas WHERE cliente_id = %s""", (cliente_id,))

    acessos = consultar_um(con, """
        SELECT COUNT(*) AS n FROM eventos_comportamentais
         WHERE cliente_id = %s AND tipo_evento = 'acesso_app' AND ocorrido_em >= %s""",
                           (cliente_id, d30))["n"]
    tem_of = consultar_um(con, """
        SELECT COUNT(*) AS n FROM consentimentos_open_finance
         WHERE cliente_id = %s AND status = 'autorizado' AND expira_em > %s""", (cliente_id, agora))["n"] > 0
    saldo = consultar_um(con, """
        SELECT AVG(t.saldo_apos) AS media FROM transacoes t JOIN contas c ON c.id = t.conta_id
         WHERE c.cliente_id = %s AND t.realizada_em BETWEEN %s AND %s""", (cliente_id, d90, agora))["media"]
    if saldo is None:
        saldo = consultar_um(con, "SELECT COALESCE(SUM(saldo_disponivel),0) AS s FROM contas WHERE cliente_id=%s",
                             (cliente_id,))["s"]

    perfil = {
        "renda_media_comprovada": round(renda, 2),
        "gasto_medio_mensal": round(gasto, 2),
        "comprometimento_renda": round(comprometimento, 2),
        "faturas_pagas_em_dia": int(fat["em_dia"] or 0),
        "faturas_atrasadas": int(fat["atrasadas"] or 0),
        "maior_atraso_dias": int(fat["maior_atraso"] or 0),
        "meses_de_relacionamento": meses,
        "frequencia_uso_app": int(acessos),
        "tem_open_finance": tem_of,
        "saldo_medio": round(D(saldo), 2),
    }
    sets = ", ".join(f"{k} = %s" for k in perfil)
    executar(con, f"UPDATE perfil_financeiro SET {sets} WHERE cliente_id = %s", (*perfil.values(), cliente_id))
    return perfil


# =====================================================================
# 3) SCORE INTERNO (0 a 1000) — modelo de pontos, fácil de explicar
# =====================================================================
def _pontuar(perfil: dict, renda_declarada, parcelas_em_dia: int, saldos_negativos: int):
    """Começa em 300 e soma/subtrai pontos por comportamento.
    Devolve (score, fatores_positivos, fatores_negativos)."""
    pos, neg = [], []

    def soma(pontos, motivo):
        if pontos > 0:
            pos.append({"fator": motivo, "pontos": int(pontos)})
        elif pontos < 0:
            neg.append({"fator": motivo, "pontos": int(pontos)})
        return pontos

    total = 300  # ponto de partida: todo cliente começa com uma chance
    em_dia = perfil["faturas_pagas_em_dia"]
    total += soma(min(300, 60 * em_dia), f"{em_dia} fatura(s) paga(s) em dia")
    total += soma(-min(360, 120 * perfil["faturas_atrasadas"]), f"{perfil['faturas_atrasadas']} fatura(s) atrasada(s)")
    total += soma(-min(150, 2 * perfil["maior_atraso_dias"]), f"Maior atraso: {perfil['maior_atraso_dias']} dias")
    total += soma(min(100, 10 * perfil["meses_de_relacionamento"]),
                  f"{perfil['meses_de_relacionamento']} mês(es) de relacionamento")
    if perfil["renda_media_comprovada"] > 0:
        total += soma(50, "Renda comprovada pela movimentação da conta")
    if perfil["renda_media_comprovada"] > 0 or (renda_declarada or 0) > 0:
        c = perfil["comprometimento_renda"]
        if c < 30:
            total += soma(100, f"Baixo comprometimento da renda ({c:.0f}%)")
        elif c < 50:
            total += soma(40, f"Comprometimento moderado da renda ({c:.0f}%)")
        else:
            total += soma(-80, f"Renda muito comprometida ({c:.0f}%)")
    if perfil["tem_open_finance"]:
        total += soma(80, "Open Finance conectado")
    if perfil["frequencia_uso_app"] >= 15:
        total += soma(40, "Usa o app com frequência")
    elif perfil["frequencia_uso_app"] >= 5:
        total += soma(20, "Usa o app regularmente")
    renda_ref = perfil["renda_media_comprovada"] or D(str(renda_declarada or 0))
    if renda_ref > 0 and perfil["saldo_medio"] >= renda_ref * D("0.10"):
        total += soma(50, "Mantém saldo na conta")
    total += soma(min(100, 20 * parcelas_em_dia), f"{parcelas_em_dia} parcela(s) de empréstimo em dia")
    total += soma(-50 * saldos_negativos, f"{saldos_negativos} vez(es) com saldo negativo")

    return max(0, min(1000, int(total))), pos, neg


def risco_por_score(score: int) -> str:
    if score >= 800: return "muito_baixo"
    if score >= 650: return "baixo"
    if score >= 500: return "medio"
    if score >= 350: return "alto"
    return "muito_alto"


def calcular_score(con, cliente_id: str) -> dict:
    perfil = consultar_um(con, "SELECT * FROM perfil_financeiro WHERE cliente_id=%s", (cliente_id,))
    renda_decl = consultar_um(con, "SELECT renda_mensal_declarada AS r FROM clientes WHERE id=%s", (cliente_id,))["r"]
    parcelas_ok = consultar_um(con, """
        SELECT COUNT(*) AS n FROM parcelas_emprestimo p
          JOIN contratos_emprestimo c ON c.id = p.contrato_id
         WHERE c.cliente_id = %s AND p.status = 'paga'""", (cliente_id,))["n"]
    negativos = consultar_um(con, """
        SELECT COUNT(*) AS n FROM eventos_comportamentais
         WHERE cliente_id = %s AND tipo_evento = 'saldo_negativo' AND ocorrido_em >= %s""",
                             (cliente_id, relogio.agora() - timedelta(days=90)))["n"]

    score, pos, neg = _pontuar(perfil, renda_decl, parcelas_ok, negativos)
    executar(con, "UPDATE perfil_financeiro SET perfil_risco=%s WHERE cliente_id=%s",
             (risco_por_score(score), cliente_id))

    ultimo = ultimo_score(con, cliente_id)
    if ultimo and ultimo["score_interno"] == score:
        return ultimo                      # nada mudou: não cria linha nova no histórico
    novo = {"cliente_id": cliente_id, "score_interno": score, "versao_modelo": config.VERSAO_MODELO_SCORE,
            "fatores_positivos": pos, "fatores_negativos": neg, "calculado_em": relogio.agora()}
    novo["id"] = inserir(con, "scores_credito", novo)
    return novo


def ultimo_score(con, cliente_id):
    s = consultar_um(con, """SELECT * FROM scores_credito WHERE cliente_id=%s
                              ORDER BY calculado_em DESC, criado_em DESC LIMIT 1""", (cliente_id,))
    if s:   # o MySQL devolve colunas JSON como texto: convertemos de volta para lista
        for campo in ("fatores_positivos", "fatores_negativos"):
            if isinstance(s[campo], str):
                s[campo] = json.loads(s[campo])
    return s


# =====================================================================
# 4) e 5) REVISÃO DO LIMITE
# =====================================================================
def _teto_por_renda(con, cliente_id, perfil) -> Decimal:
    """Por segurança, o limite nunca passa de 2x a renda (comprovada ou declarada)."""
    renda_decl = consultar_um(con, "SELECT renda_mensal_declarada AS r FROM clientes WHERE id=%s", (cliente_id,))["r"]
    renda = max(D(perfil["renda_media_comprovada"] or 0), D(str(renda_decl or 0)))
    return max(D(500), renda * 2)


def _regras_cumpridas(con, perfil, score, faturas_extra=0, meses_extra=0):
    return consultar(con, """
        SELECT * FROM regras_progressao_credito
         WHERE ativa = TRUE AND score_minimo <= %s
           AND faturas_em_dia_minimas <= %s AND meses_minimos <= %s
         ORDER BY limite_maximo DESC""",
                     (score, perfil["faturas_pagas_em_dia"] + faturas_extra,
                      perfil["meses_de_relacionamento"] + meses_extra))


def _aplicar(con, cliente_id, lim, novo, motivo, score_id=None, regra_id=None):
    anterior = D(lim["limite_total"])
    utilizado = D(lim["limite_utilizado"])
    executar(con, """UPDATE limites_credito SET limite_total=%s, limite_disponivel=%s
                      WHERE cliente_id=%s""", (novo, novo - utilizado, cliente_id))
    inserir(con, "historico_limite", {
        "cliente_id": cliente_id, "limite_anterior": anterior, "limite_novo": novo,
        "motivo": motivo, "score_id": score_id, "regra_id": regra_id, "alterado_em": relogio.agora()})
    auditar(con, "alterou_limite", "limites_credito", lim["id"],
            {"limite_total": anterior}, {"limite_total": novo, "motivo": motivo})
    if novo > anterior:
        notificacoes.notificar(con, cliente_id, "limite", "Seu limite subiu!",
                               f"Seu limite passou de R$ {anterior:,.2f} para R$ {novo:,.2f}. Continue assim!")
    else:
        notificacoes.notificar(con, cliente_id, "limite", "Seu limite foi ajustado",
                               f"Seu limite agora é R$ {novo:,.2f}. Pague em dia para voltar a crescer.")
    return {"anterior": float(anterior), "novo": float(novo), "motivo": motivo}


def revisar_limite(con, cliente_id: str, gatilho: str):
    lim = consultar_um(con, "SELECT * FROM limites_credito WHERE cliente_id=%s FOR UPDATE", (cliente_id,))
    perfil = consultar_um(con, "SELECT * FROM perfil_financeiro WHERE cliente_id=%s", (cliente_id,))
    score = ultimo_score(con, cliente_id)
    hoje = relogio.hoje()
    total = D(lim["limite_total"])
    teto = _teto_por_renda(con, cliente_id, perfil)
    resultado = None

    if gatilho == "fatura_atrasada":
        # Atraso: reduz 20% (nunca abaixo do que já está usado) e adia a próxima revisão
        novo = max(D(lim["limite_utilizado"]), _arred(total * D("0.8"), 10))
        if novo < total:
            resultado = _aplicar(con, cliente_id, lim, novo, "reducao_risco", score["id"])
        executar(con, "UPDATE limites_credito SET proxima_revisao_em=%s WHERE cliente_id=%s",
                 (hoje + timedelta(days=60), cliente_id))

    elif gatilho == "open_finance_conectado":
        # Bônus único de 20% por trazer o histórico de outros bancos
        ja_ganhou = consultar_um(con, """SELECT COUNT(*) AS n FROM historico_limite
                                          WHERE cliente_id=%s AND motivo='open_finance'""", (cliente_id,))["n"]
        novo = min(_arred(total * D("1.2"), 10), teto)
        if not ja_ganhou and novo > total:
            resultado = _aplicar(con, cliente_id, lim, novo, "open_finance", score["id"])

    elif gatilho == "fatura_paga_em_dia":
        if lim["proxima_revisao_em"] is None or hoje >= lim["proxima_revisao_em"]:
            regras = _regras_cumpridas(con, perfil, score["score_interno"])
            if regras:
                regra = regras[0]   # a regra mais avançada que o cliente cumpre
                novo = min(_arred(total * (1 + D(regra["percentual_aumento"]) / 100), 10),
                           D(regra["limite_maximo"]), teto)
                if novo > total:
                    resultado = _aplicar(con, cliente_id, lim, novo, "aumento_automatico",
                                         score["id"], regra["id"])
            executar(con, "UPDATE limites_credito SET proxima_revisao_em=%s WHERE cliente_id=%s",
                     (hoje + timedelta(days=25), cliente_id))

    atualizar_previsoes(con, cliente_id)
    return resultado


def aumento_por_beneficio(con, cliente_id: str, percentual):
    """Benefício 'aumento_limite' liberado ao subir de nível."""
    lim = consultar_um(con, "SELECT * FROM limites_credito WHERE cliente_id=%s FOR UPDATE", (cliente_id,))
    perfil = consultar_um(con, "SELECT * FROM perfil_financeiro WHERE cliente_id=%s", (cliente_id,))
    total = D(lim["limite_total"])
    novo = min(_arred(total * (1 + D(str(percentual)) / 100), 10), _teto_por_renda(con, cliente_id, perfil))
    if novo > total:
        score = ultimo_score(con, cliente_id)
        r = _aplicar(con, cliente_id, lim, novo, "subida_nivel", score["id"] if score else None)
        atualizar_previsoes(con, cliente_id)
        return r
    return None


def atualizar_previsoes(con, cliente_id: str):
    """Calcula o 'próximo limite previsto' (mostrado na tela) e o pré-aprovado de empréstimo."""
    lim = consultar_um(con, "SELECT * FROM limites_credito WHERE cliente_id=%s", (cliente_id,))
    perfil = consultar_um(con, "SELECT * FROM perfil_financeiro WHERE cliente_id=%s", (cliente_id,))
    score = ultimo_score(con, cliente_id)
    total = D(lim["limite_total"])
    teto = _teto_por_renda(con, cliente_id, perfil)

    # "Se pagar a próxima fatura em dia, qual regra vai valer?"
    regras = _regras_cumpridas(con, perfil, score["score_interno"], faturas_extra=1, meses_extra=1)
    previsto = total
    if regras:
        r = regras[0]
        previsto = max(total, min(_arred(total * (1 + D(r["percentual_aumento"]) / 100), 10),
                                  D(r["limite_maximo"]), teto))

    s = score["score_interno"]
    renda = max(D(perfil["renda_media_comprovada"] or 0), D(0))
    # Empréstimo pré-aprovado: até 1,5x a renda comprovada, proporcional ao score
    pre_aprovado = D(0) if s < 450 or renda <= 0 else min(_arred(renda * s / 1000 * D("1.5"), 100), D(15000))

    executar(con, """UPDATE limites_credito SET proximo_limite_previsto=%s, limite_emprestimo_pre_aprovado=%s
                      WHERE cliente_id=%s""", (previsto, pre_aprovado, cliente_id))


# =====================================================================
# Uso do limite pelo cartão
# =====================================================================
def usar_limite(con, cliente_id, valor) -> bool:
    lim = consultar_um(con, "SELECT * FROM limites_credito WHERE cliente_id=%s FOR UPDATE", (cliente_id,))
    valor = D(str(valor))
    if D(lim["limite_disponivel"]) < valor:
        return False
    executar(con, """UPDATE limites_credito SET limite_utilizado = limite_utilizado + %s,
                            limite_disponivel = limite_total - (limite_utilizado) WHERE cliente_id=%s""",
             (valor, cliente_id))
    return True


def liberar_limite(con, cliente_id, valor):
    executar(con, """UPDATE limites_credito
                        SET limite_utilizado = GREATEST(0, limite_utilizado - %s),
                            limite_disponivel = limite_total - GREATEST(0, limite_utilizado)
                      WHERE cliente_id=%s""", (D(str(valor)), cliente_id))
