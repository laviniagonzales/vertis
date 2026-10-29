"""
CARTÕES E FATURAS (módulo 3 do roteiro)
======================================
Regra-chave: o CARTÃO NÃO GUARDA O LIMITE. O limite fica em
`limites_credito`, então quando o limite sobe vale para todos os cartões.

Ciclo da fatura (mês de referência M):
   compras ... | FECHAMENTO (7 dias antes) | VENCIMENTO (dia 10)
   Compra feita depois do fechamento cai na fatura do mês seguinte.
"""
import calendar
import random
import secrets
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import config
import relogio
from db import consultar, consultar_um, executar, inserir, auditar
from servicos import conta as conta_srv, credito, eventos, notificacoes

D = Decimal


# ---------------------------------------------------------------- emissão
def emitir(con, conta_id, nome_impresso, formato="virtual", funcao="multiplo", status="ativo"):
    hoje = relogio.hoje()
    return inserir(con, "cartoes", {
        "conta_id": conta_id, "formato": formato, "funcao": funcao, "bandeira": "Mastercard",
        "final_cartao": f"{random.randint(0, 9999):04d}",
        "token_processador": "tok_" + secrets.token_hex(16),   # número completo fica no processador
        "nome_impresso": nome_impresso.upper()[:26],
        "validade": f"{hoje.month:02d}/{(hoje.year + 6) % 100:02d}",
        "dia_vencimento_fatura": config.DIA_VENCIMENTO_PADRAO,
        "status": status, "emitido_em": relogio.agora() if status == "ativo" else None})


def cartoes(con, cliente_id):
    return consultar(con, """
        SELECT ca.id, ca.formato, ca.funcao, ca.bandeira, ca.final_cartao, ca.nome_impresso, ca.validade,
               ca.dia_vencimento_fatura, ca.aproximacao_ativa, ca.compras_internacionais, ca.status
          FROM cartoes ca JOIN contas c ON c.id = ca.conta_id
         WHERE c.cliente_id = %s AND ca.status <> 'cancelado'
         ORDER BY ca.formato = 'virtual' DESC, ca.criado_em""", (cliente_id,))


def alternar_bloqueio(con, cliente_id, cartao_id):
    c = consultar_um(con, """SELECT ca.* FROM cartoes ca JOIN contas c ON c.id = ca.conta_id
                              WHERE ca.id=%s AND c.cliente_id=%s""", (cartao_id, cliente_id))
    if not c or c["status"] not in ("ativo", "bloqueado_temporario"):
        raise ValueError("Cartão não pode ser bloqueado/desbloqueado")
    novo = "bloqueado_temporario" if c["status"] == "ativo" else "ativo"
    executar(con, "UPDATE cartoes SET status=%s WHERE id=%s", (novo, cartao_id))
    auditar(con, "bloqueou_cartao" if novo != "ativo" else "desbloqueou_cartao", "cartoes", cartao_id,
            {"status": c["status"]}, {"status": novo}, ator_tipo="cliente", ator_id=cliente_id)
    return novo


# ---------------------------------------------------------------- datas da fatura
def _vencimento(ano, mes, dia) -> date:
    return date(ano, mes, min(dia, calendar.monthrange(ano, mes)[1]))


def _somar_meses(ano, mes, n):
    total = ano * 12 + (mes - 1) + n
    return total // 12, total % 12 + 1


def fatura_do_mes(con, cliente_id, ano, mes, dia_venc) -> dict:
    """Busca a fatura do mês; se não existir, cria (status 'aberta')."""
    ref = f"{ano:04d}-{mes:02d}"
    f = consultar_um(con, "SELECT * FROM faturas WHERE cliente_id=%s AND mes_referencia=%s", (cliente_id, ref))
    if f:
        return f
    venc = _vencimento(ano, mes, dia_venc)
    inserir(con, "faturas", {"cliente_id": cliente_id, "mes_referencia": ref,
                             "data_fechamento": venc - timedelta(days=config.DIAS_ANTES_FECHAMENTO),
                             "data_vencimento": venc, "status": "aberta"})
    return consultar_um(con, "SELECT * FROM faturas WHERE cliente_id=%s AND mes_referencia=%s", (cliente_id, ref))


def mes_da_compra(dia: date, dia_venc: int) -> tuple[int, int]:
    """Em qual fatura cai uma compra feita em `dia`?"""
    ano, mes = dia.year, dia.month
    while dia >= _vencimento(ano, mes, dia_venc) - timedelta(days=config.DIAS_ANTES_FECHAMENTO):
        ano, mes = _somar_meses(ano, mes, 1)
    return ano, mes


# ---------------------------------------------------------------- compras
def comprar(con, cliente_id, valor, estabelecimento, parcelas=1, categoria="Compras",
            funcao="credito", cartao_id=None, mcc=None) -> dict:
    valor = D(str(valor)).quantize(D("0.01"))
    parcelas = max(1, int(parcelas))
    filtro = "AND ca.id = %s" if cartao_id else ""
    params = (cliente_id, cartao_id) if cartao_id else (cliente_id,)
    cartao = consultar_um(con, f"""
        SELECT ca.* FROM cartoes ca JOIN contas c ON c.id = ca.conta_id
         WHERE c.cliente_id = %s AND ca.status IN ('ativo','bloqueado_temporario') {filtro}
         ORDER BY ca.formato = 'virtual' DESC LIMIT 1""", params)
    if not cartao:
        raise ValueError("Nenhum cartão encontrado")

    compra = {"cartao_id": cartao["id"], "estabelecimento": estabelecimento[:150], "mcc": mcc,
              "categoria_id": conta_srv.categoria_id(con, categoria), "valor_total": valor,
              "num_parcelas": parcelas if funcao == "credito" else 1, "funcao_usada": funcao,
              "realizada_em": relogio.agora()}

    motivo = None
    if cartao["status"] != "ativo":
        motivo = "Cartão bloqueado"
    elif funcao == "credito" and not credito.usar_limite(con, cliente_id, valor):
        motivo = "Limite insuficiente"
    if motivo:
        compra.update(status="negada", motivo_negativa=motivo)
        compra["id"] = inserir(con, "compras_cartao", compra)
        return compra

    compra["status"] = "autorizada"
    compra["id"] = inserir(con, "compras_cartao", compra)

    if funcao == "debito":
        c = conta_srv.conta_do_cliente(con, cliente_id)
        conta_srv.lancar(con, c["id"], "compra_debito", "saida", valor, f"Compra {estabelecimento}",
                         categoria=categoria, contraparte_nome=estabelecimento)
    else:
        # Divide em parcelas; a última absorve os centavos que sobram
        base = (valor / parcelas).quantize(D("0.01"), rounding=ROUND_HALF_UP)
        ano, mes = mes_da_compra(relogio.hoje(), cartao["dia_vencimento_fatura"])
        for k in range(parcelas):
            v = base if k < parcelas - 1 else valor - base * (parcelas - 1)
            a, m = _somar_meses(ano, mes, k)
            fat = fatura_do_mes(con, cliente_id, a, m, cartao["dia_vencimento_fatura"])
            inserir(con, "lancamentos_fatura", {
                "fatura_id": fat["id"], "compra_id": compra["id"],
                "tipo": "compra" if parcelas == 1 else "parcela",
                "numero_parcela": k + 1 if parcelas > 1 else None, "valor": v,
                "descricao": estabelecimento if parcelas == 1 else f"{estabelecimento} ({k + 1}/{parcelas})"})
            executar(con, "UPDATE faturas SET valor_total = valor_total + %s WHERE id=%s", (v, fat["id"]))

    eventos.registrar(con, cliente_id, "compra_realizada", "cartao", compra["id"], valor,
                      {"estabelecimento": estabelecimento, "funcao": funcao})
    return compra


# ---------------------------------------------------------------- rotina diária
def processar_ciclo(con, cliente_id):
    """Fecha faturas, marca atrasos. Chamado sempre que o cliente usa o app
    (e a cada dia simulado no modo demonstração)."""
    hoje = relogio.hoje()

    for f in consultar(con, """SELECT * FROM faturas WHERE cliente_id=%s AND status='aberta'
                                AND data_fechamento <= %s""", (cliente_id, hoje)):
        total = consultar_um(con, """
            SELECT COALESCE(SUM(CASE WHEN tipo IN ('estorno','pagamento') THEN -valor ELSE valor END), 0) AS t
              FROM lancamentos_fatura WHERE fatura_id=%s AND tipo <> 'pagamento'""", (f["id"],))["t"]
        total = D(total)
        if total <= 0:
            executar(con, """UPDATE faturas SET status='paga', valor_total=0, valor_minimo=0, pago_em=%s
                              WHERE id=%s""", (relogio.agora(), f["id"]))
            continue
        minimo = min(total, max(D(50), (total * D("0.15")).quantize(D("0.01"))))
        executar(con, "UPDATE faturas SET status='fechada', valor_total=%s, valor_minimo=%s WHERE id=%s",
                 (total, minimo, f["id"]))
        notificacoes.notificar(con, cliente_id, "fatura", "Sua fatura fechou",
                               f"Valor R$ {total:,.2f} — vence em {f['data_vencimento']:%d/%m}.", f["id"])

    for f in consultar(con, """SELECT * FROM faturas WHERE cliente_id=%s
                                AND status IN ('fechada','paga_parcial','atrasada')
                                AND data_vencimento < %s AND valor_pago < valor_total""", (cliente_id, hoje)):
        dias = (hoje - f["data_vencimento"]).days
        executar(con, "UPDATE faturas SET status='atrasada', dias_atraso=%s WHERE id=%s", (dias, f["id"]))
        if f["status"] != "atrasada":     # acabou de atrasar: multa de 2% + evento negativo
            multa = (D(f["valor_total"]) * D("0.02")).quantize(D("0.01"))
            inserir(con, "lancamentos_fatura", {"fatura_id": f["id"], "tipo": "multa", "valor": multa,
                                                "descricao": "Multa por atraso (2%)"})
            executar(con, "UPDATE faturas SET valor_total = valor_total + %s WHERE id=%s", (multa, f["id"]))
            notificacoes.notificar(con, cliente_id, "fatura", "Fatura em atraso",
                                   "Pague o quanto antes para não prejudicar seu limite.", f["id"])
            eventos.registrar(con, cliente_id, "fatura_atrasada", "cartao", f["id"], f["valor_total"],
                              {"dias_atraso": dias})


# ---------------------------------------------------------------- pagamento
def pagar_fatura(con, cliente_id, fatura_id, valor=None) -> dict:
    f = consultar_um(con, "SELECT * FROM faturas WHERE id=%s AND cliente_id=%s FOR UPDATE", (fatura_id, cliente_id))
    if not f or f["status"] not in ("fechada", "paga_parcial", "atrasada"):
        raise ValueError("Esta fatura não está disponível para pagamento")
    restante = D(f["valor_total"]) - D(f["valor_pago"])
    valor = restante if valor is None else min(D(str(valor)), restante)
    if valor <= 0:
        raise ValueError("Valor inválido")

    c = conta_srv.conta_do_cliente(con, cliente_id)
    t = conta_srv.lancar(con, c["id"], "pagamento_fatura", "saida", valor,
                         f"Pagamento fatura {f['mes_referencia']}", categoria="Contas e serviços",
                         contraparte_nome="Cartão Vértis")
    inserir(con, "lancamentos_fatura", {"fatura_id": fatura_id, "tipo": "pagamento", "valor": valor,
                                        "descricao": "Pagamento recebido"})
    novo_pago = D(f["valor_pago"]) + valor
    quitou = novo_pago >= D(f["valor_total"])
    agora = relogio.agora()
    executar(con, "UPDATE faturas SET valor_pago=%s, status=%s, pago_em=%s WHERE id=%s",
             (novo_pago, "paga" if quitou else "paga_parcial", agora if quitou else None, fatura_id))
    credito.liberar_limite(con, cliente_id, valor)   # o limite volta a ficar disponível

    resultado = {"transacao_id": t["id"], "valor_pago": float(valor), "quitada": quitou, "efeitos": None}
    if quitou and agora.date() <= f["data_vencimento"]:
        resultado["efeitos"] = eventos.registrar(con, cliente_id, "fatura_paga_em_dia", "cartao",
                                                 fatura_id, f["valor_total"])
    else:
        credito.atualizar_perfil(con, cliente_id)
        credito.calcular_score(con, cliente_id)
    return resultado


def faturas(con, cliente_id, limite=6):
    lista = consultar(con, """SELECT * FROM faturas WHERE cliente_id=%s
                               ORDER BY mes_referencia DESC LIMIT %s""", (cliente_id, limite))
    for f in lista:
        f["lancamentos"] = consultar(con, """SELECT tipo, numero_parcela, valor, descricao, criado_em
                                              FROM lancamentos_fatura WHERE fatura_id=%s
                                             ORDER BY criado_em""", (f["id"],))
    return lista
