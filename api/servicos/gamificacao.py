"""
TRILHA 2 — GAMIFICAÇÃO (módulo 7 do roteiro)
============================================
O cliente acumula 3 "moedas":
  • XP      → faz SUBIR DE NÍVEL (não é gasto)
  • pontos  → podem ser trocados (cashback, produtos)
  • milhas  → podem ser transferidas para companhias aéreas

Todo ganho ou gasto vira uma linha em `movimentacoes_recompensa`
(funciona como o extrato da conta, só que de recompensas).
"""
import random
import string
from datetime import timedelta
from decimal import Decimal

import config
import relogio
from db import consultar, consultar_um, executar, inserir, auditar
from servicos import credito, notificacoes

D = Decimal
VALIDADE_PONTOS_MESES = 24


# ---------------------------------------------------------------- consultas básicas
def progresso(con, cliente_id):
    return consultar_um(con, """
        SELECT p.*, n.ordem AS nivel_ordem, n.nome AS nivel_nome, n.cor_hex AS nivel_cor,
               n.multiplicador_pontos
          FROM progresso_cliente p JOIN niveis n ON n.id = p.nivel_id
         WHERE p.cliente_id = %s""", (cliente_id,))


def multiplicador_total(con, cliente_id) -> Decimal:
    """Multiplicador do nível + benefícios do tipo 'multiplicador' liberados."""
    prog = progresso(con, cliente_id)
    extra = consultar_um(con, """
        SELECT COALESCE(SUM(b.valor), 0) AS pct FROM beneficios_cliente bc
          JOIN beneficios b ON b.id = bc.beneficio_id
         WHERE bc.cliente_id = %s AND bc.status = 'liberado' AND b.tipo = 'multiplicador'""",
                         (cliente_id,))["pct"]
    return D(prog["multiplicador_pontos"]) + D(extra) / 100


# ---------------------------------------------------------------- créditos e débitos
def movimentar(con, cliente_id, moeda, quantidade, tipo="credito", descricao=None,
               evento_id=None, regra_id=None, resgate_id=None) -> int:
    """Credita ou debita XP/pontos/milhas e registra no extrato de recompensas."""
    if quantidade <= 0:
        return 0
    coluna = {"xp": "xp_total", "pontos": "saldo_pontos", "milhas": "saldo_milhas"}[moeda]
    sinal = 1 if tipo in ("credito", "estorno") else -1
    executar(con, f"UPDATE progresso_cliente SET {coluna} = {coluna} + %s WHERE cliente_id = %s",
             (sinal * quantidade, cliente_id))
    saldo = consultar_um(con, f"SELECT {coluna} AS s FROM progresso_cliente WHERE cliente_id=%s",
                         (cliente_id,))["s"]
    expira = None
    if moeda != "xp" and tipo == "credito":
        expira = relogio.hoje() + timedelta(days=30 * VALIDADE_PONTOS_MESES)
    inserir(con, "movimentacoes_recompensa", {
        "cliente_id": cliente_id, "moeda": moeda, "tipo": tipo, "quantidade": quantidade,
        "saldo_apos": saldo, "evento_id": evento_id, "regra_id": regra_id, "resgate_id": resgate_id,
        "descricao": (descricao or "")[:150], "expira_em": expira, "ocorrido_em": relogio.agora()})
    if moeda == "xp":
        verificar_nivel(con, cliente_id)
    return quantidade


DESCRICOES = {
    "fatura_paga_em_dia": "Fatura paga em dia", "salario_recebido": "Salário recebido na Vértis",
    "deposito_recebido": "Depósito recebido", "compra_realizada": "Compra no cartão",
    "acesso_app": "Acesso diário ao app", "meta_atingida": "Meta financeira atingida",
    "open_finance_conectado": "Open Finance conectado", "parcela_paga": "Parcela paga",
}


# ---------------------------------------------------------------- processar um evento
def processar_evento(con, evento: dict) -> dict:
    cliente_id, tipo = evento["cliente_id"], evento["tipo_evento"]
    hoje = relogio.hoje()
    ganhos = {"xp": 0, "pontos": 0, "milhas": 0}

    regra = consultar_um(con, """
        SELECT * FROM regras_pontuacao
         WHERE tipo_evento = %s AND ativa = TRUE
           AND (valida_de IS NULL OR valida_de <= %s) AND (valida_ate IS NULL OR valida_ate >= %s)
         ORDER BY criado_em DESC LIMIT 1""", (tipo, hoje, hoje))

    if regra:
        dentro_do_limite = True
        if regra["limite_diario"]:
            usadas_hoje = consultar_um(con, """
                SELECT COUNT(*) AS n FROM movimentacoes_recompensa
                 WHERE cliente_id = %s AND regra_id = %s AND moeda = 'xp' AND DATE(ocorrido_em) = %s""",
                                       (cliente_id, regra["id"], hoje))["n"]
            dentro_do_limite = usadas_hoje < regra["limite_diario"]

        if dentro_do_limite:
            mult = multiplicador_total(con, cliente_id)
            pontos = D(regra["pontos_ganhos"])
            if regra["pontos_por_real"] and evento.get("valor"):
                pontos += D(regra["pontos_por_real"]) * D(evento["valor"])
            pontos = int(pontos * mult)
            desc = DESCRICOES.get(tipo, tipo)
            ids = dict(evento_id=evento["id"], regra_id=regra["id"], descricao=desc)
            # milhas e pontos primeiro; XP por último (pode disparar subida de nível)
            ganhos["pontos"] = movimentar(con, cliente_id, "pontos", pontos, **ids)
            ganhos["milhas"] = movimentar(con, cliente_id, "milhas", regra["milhas_ganhas"], **ids)
            ganhos["xp"] = movimentar(con, cliente_id, "xp", regra["xp_ganho"], **ids)

    conquistas = avancar_conquistas(con, cliente_id, tipo)
    atualizar_proxima_conquista(con, cliente_id)
    return {**ganhos, "conquistas": conquistas}


# ---------------------------------------------------------------- níveis
def verificar_nivel(con, cliente_id):
    prog = progresso(con, cliente_id)
    novo = consultar_um(con, """SELECT * FROM niveis WHERE xp_minimo <= %s
                                 ORDER BY ordem DESC LIMIT 1""", (prog["xp_total"],))
    proximo = consultar_um(con, "SELECT xp_minimo FROM niveis WHERE ordem = %s", (novo["ordem"] + 1,))
    falta = max(0, proximo["xp_minimo"] - prog["xp_total"]) if proximo else 0
    executar(con, "UPDATE progresso_cliente SET xp_para_proximo_nivel=%s WHERE cliente_id=%s", (falta, cliente_id))

    if novo["ordem"] <= prog["nivel_ordem"]:
        return None

    # Subiu! (pode ter pulado mais de um nível de uma vez)
    executar(con, "UPDATE progresso_cliente SET nivel_id=%s, subiu_nivel_em=%s WHERE cliente_id=%s",
             (novo["id"], relogio.agora(), cliente_id))
    auditar(con, "subiu_nivel", "progresso_cliente", prog["id"],
            {"nivel": prog["nivel_nome"]}, {"nivel": novo["nome"]})
    notificacoes.notificar(con, cliente_id, "nivel", f"Você chegou ao nível {novo['nome']}!",
                           f"Parabéns! Agora seus pontos rendem {novo['multiplicador_pontos']}x.", novo["id"])

    # Benefícios do nível (os que NÃO dependem de conquista)
    beneficios = consultar(con, """
        SELECT b.* FROM beneficios b JOIN niveis n ON n.id = b.nivel_minimo_id
         WHERE b.ativo = TRUE AND n.ordem > %s AND n.ordem <= %s
           AND b.id NOT IN (SELECT beneficio_id FROM conquistas WHERE beneficio_id IS NOT NULL)""",
                           (prog["nivel_ordem"], novo["ordem"]))
    for b in beneficios:
        liberar_beneficio(con, cliente_id, b, origem="nivel")

    # Conquistas que dependem só de nível (ex.: "Nível VIP Nacional")
    for c in consultar(con, """
            SELECT c.*, cc.id AS cc_id FROM conquistas c
              JOIN conquistas_cliente cc ON cc.conquista_id = c.id AND cc.cliente_id = %s
              JOIN niveis n ON n.id = c.nivel_minimo_id
             WHERE c.criterio_tipo_evento IS NULL AND c.ativa = TRUE
               AND cc.status <> 'conquistada' AND n.ordem <= %s""", (cliente_id, novo["ordem"])):
        concluir_conquista(con, cliente_id, c)
    return novo


# ---------------------------------------------------------------- conquistas
def avancar_conquistas(con, cliente_id, tipo_evento) -> list[str]:
    prog = progresso(con, cliente_id)
    ganhas = []
    for c in consultar(con, """
            SELECT c.*, cc.id AS cc_id, cc.progresso_atual, n.ordem AS nivel_min
              FROM conquistas c
              JOIN conquistas_cliente cc ON cc.conquista_id = c.id AND cc.cliente_id = %s
              LEFT JOIN niveis n ON n.id = c.nivel_minimo_id
             WHERE c.criterio_tipo_evento = %s AND c.ativa = TRUE AND cc.status <> 'conquistada'""",
                       (cliente_id, tipo_evento)):
        if c["nivel_min"] and prog["nivel_ordem"] < c["nivel_min"]:
            continue
        novo_progresso = c["progresso_atual"] + 1
        executar(con, "UPDATE conquistas_cliente SET progresso_atual=%s, status='em_andamento' WHERE id=%s",
                 (novo_progresso, c["cc_id"]))
        if novo_progresso >= c["criterio_quantidade"]:
            concluir_conquista(con, cliente_id, c)
            ganhas.append(c["nome"])
    return ganhas


def concluir_conquista(con, cliente_id, c):
    executar(con, """UPDATE conquistas_cliente
                        SET status='conquistada', conquistada_em=%s, progresso_atual=%s, visualizada=FALSE
                      WHERE id=%s""", (relogio.agora(), c["criterio_quantidade"], c["cc_id"]))
    notificacoes.notificar(con, cliente_id, "conquista", f"Conquista: {c['nome']}!",
                           c["descricao"] or "", c["id"])
    desc = f"Conquista: {c['nome']}"
    movimentar(con, cliente_id, "pontos", c["pontos_recompensa"], descricao=desc)
    if c["beneficio_id"]:
        b = consultar_um(con, "SELECT * FROM beneficios WHERE id=%s", (c["beneficio_id"],))
        liberar_beneficio(con, cliente_id, b, origem="conquista")
    movimentar(con, cliente_id, "xp", c["xp_recompensa"], descricao=desc)


def atualizar_proxima_conquista(con, cliente_id):
    """Escolhe a conquista mais perto de ser completada (destaque 'Próxima conquista')."""
    prog = progresso(con, cliente_id)
    melhor, melhor_pct = None, -1.0
    for c in consultar(con, """
            SELECT c.id, c.criterio_tipo_evento, c.criterio_quantidade, cc.progresso_atual, n.xp_minimo
              FROM conquistas c
              JOIN conquistas_cliente cc ON cc.conquista_id = c.id AND cc.cliente_id = %s
              LEFT JOIN niveis n ON n.id = c.nivel_minimo_id
             WHERE cc.status <> 'conquistada' AND c.ativa = TRUE""", (cliente_id,)):
        if c["criterio_tipo_evento"] is None and c["xp_minimo"]:
            pct = prog["xp_total"] / c["xp_minimo"]
        else:
            pct = c["progresso_atual"] / max(1, c["criterio_quantidade"])
        if pct > melhor_pct:
            melhor, melhor_pct = c["id"], pct
    executar(con, "UPDATE progresso_cliente SET proxima_conquista_id=%s WHERE cliente_id=%s", (melhor, cliente_id))


# ---------------------------------------------------------------- benefícios
def liberar_beneficio(con, cliente_id, b, origem):
    ja_tem = consultar_um(con, """SELECT id FROM beneficios_cliente
                                   WHERE cliente_id=%s AND beneficio_id=%s AND status='liberado'""",
                          (cliente_id, b["id"]))
    if ja_tem:
        return
    voucher = None
    if b["tipo"] == "sala_vip":
        voucher = "VIP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    inserir(con, "beneficios_cliente", {
        "cliente_id": cliente_id, "beneficio_id": b["id"], "origem": origem, "status": "liberado",
        "usos_restantes": b["usos_por_mes"], "codigo_voucher": voucher, "liberado_em": relogio.agora(),
        "expira_em": relogio.agora() + timedelta(days=365)})
    notificacoes.notificar(con, cliente_id, "conquista", f"{b['nome']} LIBERADO!",
                           "Um novo benefício está disponível para você.", b["id"])
    if b["tipo"] == "aumento_limite" and b["valor"]:
        credito.aumento_por_beneficio(con, cliente_id, b["valor"])


# ---------------------------------------------------------------- resgates
def resgatar(con, cliente_id, tipo, quantidade: int, parceiro_id=None) -> dict:
    """Troca pontos por cashback (cai na conta) ou milhas para um parceiro aéreo."""
    prog = progresso(con, cliente_id)
    if tipo == "cashback":
        moeda, saldo = "pontos", prog["saldo_pontos"]
        valor = D(quantidade) / config.PONTOS_POR_REAL_CASHBACK
    elif tipo == "transferencia_milhas":
        moeda, saldo = "milhas", prog["saldo_milhas"]
        parceiro = consultar_um(con, "SELECT * FROM parceiros WHERE id=%s AND ativo=TRUE", (parceiro_id,))
        if not parceiro:
            raise ValueError("Parceiro inválido")
        valor = None
    else:
        raise ValueError("Tipo de resgate não suportado")
    if quantidade <= 0 or quantidade > saldo:
        raise ValueError(f"Saldo de {moeda} insuficiente")

    resgate_id = inserir(con, "resgates", {
        "cliente_id": cliente_id, "tipo": tipo, "parceiro_id": parceiro_id, "moeda_usada": moeda,
        "quantidade_usada": quantidade, "valor_equivalente": valor, "status": "concluido",
        "solicitado_em": relogio.agora(), "concluido_em": relogio.agora()})
    movimentar(con, cliente_id, moeda, quantidade, tipo="debito",
               descricao=f"Resgate: {tipo.replace('_', ' ')}", resgate_id=resgate_id)

    if tipo == "cashback":
        from servicos import conta   # import aqui para evitar import circular
        c = conta.conta_do_cliente(con, cliente_id)
        conta.lancar(con, c["id"], "deposito", "entrada", valor, "Cashback de pontos Vértis",
                     categoria="Outras receitas", contraparte_nome="Vértis Recompensas")
    return {"resgate_id": resgate_id, "moeda": moeda, "quantidade": quantidade,
            "valor_reais": float(valor) if valor else None}
