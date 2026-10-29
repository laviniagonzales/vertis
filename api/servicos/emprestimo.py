"""
EMPRÉSTIMO PERSONALIZADO (módulo 5)
==================================
A taxa depende do PERFIL DE RISCO do momento: quanto melhor o
comportamento, menor a taxa. Parcelas pela TABELA PRICE (parcelas iguais):

        PMT = PV × i / (1 − (1 + i)^−n)
   PV = valor emprestado, i = taxa ao mês, n = número de parcelas
"""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

import relogio
from db import consultar, consultar_um, executar, inserir, auditar
from servicos import conta as conta_srv, credito, eventos

D = Decimal
TAXA_POR_RISCO = {"muito_baixo": D("1.99"), "baixo": D("2.99"), "medio": D("3.99"), "alto": D("5.49")}


def parcela_price(valor, taxa_mensal_pct, n) -> Decimal:
    i = D(taxa_mensal_pct) / 100
    pmt = D(valor) * i / (1 - (1 + i) ** -n)
    return pmt.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def simular(con, cliente_id, valor, num_parcelas, finalidade=None) -> dict:
    perfil = consultar_um(con, "SELECT perfil_risco FROM perfil_financeiro WHERE cliente_id=%s", (cliente_id,))
    lim = consultar_um(con, "SELECT limite_emprestimo_pre_aprovado AS pre FROM limites_credito WHERE cliente_id=%s",
                       (cliente_id,))
    score = credito.ultimo_score(con, cliente_id)
    taxa = TAXA_POR_RISCO.get(perfil["perfil_risco"])
    valor = D(str(valor))
    proposta = {"cliente_id": cliente_id, "score_id": score["id"], "valor_solicitado": valor,
                "num_parcelas": int(num_parcelas), "finalidade": finalidade,
                "validade_ate": relogio.agora() + timedelta(days=7)}
    if taxa is None or D(lim["pre"]) <= 0:
        proposta["status"] = "recusada"
        proposta["id"] = inserir(con, "propostas_emprestimo", proposta)
        return {**proposta, "motivo": "Ainda não há crédito pré-aprovado. Pague suas faturas em dia para liberar."}

    aprovado = min(valor, D(lim["pre"]))
    pmt = parcela_price(aprovado, taxa, int(num_parcelas))
    cet = (((1 + taxa / 100) ** 12) - 1) * 100       # CET simplificado (sem IOF e tarifas)
    proposta.update(valor_aprovado=aprovado, taxa_juros_mensal=taxa, cet_anual=cet.quantize(D("0.01")),
                    valor_parcela=pmt, status="simulada")
    proposta["id"] = inserir(con, "propostas_emprestimo", proposta)
    return proposta


def contratar(con, cliente_id, proposta_id) -> dict:
    p = consultar_um(con, """SELECT * FROM propostas_emprestimo WHERE id=%s AND cliente_id=%s FOR UPDATE""",
                     (proposta_id, cliente_id))
    if not p or p["status"] not in ("simulada", "aprovada"):
        raise ValueError("Proposta indisponível")
    if p["validade_ate"] < relogio.agora():
        executar(con, "UPDATE propostas_emprestimo SET status='expirada' WHERE id=%s", (proposta_id,))
        raise ValueError("Proposta expirada")
    conta = conta_srv.conta_do_cliente(con, cliente_id)
    hoje = relogio.hoje()
    numero = "VTS" + relogio.agora().strftime("%y%m%d%H%M%S")
    contrato_id = inserir(con, "contratos_emprestimo", {
        "proposta_id": proposta_id, "cliente_id": cliente_id, "conta_id": conta["id"], "numero_contrato": numero,
        "valor_contratado": p["valor_aprovado"], "saldo_devedor": D(p["valor_parcela"]) * p["num_parcelas"],
        "data_primeira_parcela": hoje + timedelta(days=30), "assinado_em": relogio.agora()})
    for k in range(p["num_parcelas"]):
        inserir(con, "parcelas_emprestimo", {"contrato_id": contrato_id, "numero_parcela": k + 1,
                                             "valor": p["valor_parcela"], "vencimento": hoje + timedelta(days=30 * (k + 1))})
    executar(con, "UPDATE propostas_emprestimo SET status='contratada' WHERE id=%s", (proposta_id,))
    conta_srv.lancar(con, conta["id"], "credito_emprestimo", "entrada", p["valor_aprovado"],
                     f"Empréstimo {numero}", categoria="Outras receitas", contraparte_nome="Vértis Crédito")
    auditar(con, "contratou_emprestimo", "contratos_emprestimo", contrato_id, None,
            {"valor": p["valor_aprovado"]}, ator_tipo="cliente", ator_id=cliente_id)
    credito.atualizar_perfil(con, cliente_id)
    return {"contrato_id": contrato_id, "numero_contrato": numero}


def pagar_parcela(con, cliente_id, parcela_id) -> dict:
    p = consultar_um(con, """SELECT p.*, c.id AS contrato, c.cliente_id FROM parcelas_emprestimo p
                              JOIN contratos_emprestimo c ON c.id = p.contrato_id
                             WHERE p.id=%s AND c.cliente_id=%s FOR UPDATE""", (parcela_id, cliente_id))
    if not p or p["status"] in ("paga", "paga_atrasada"):
        raise ValueError("Parcela indisponível")
    hoje = relogio.hoje()
    atrasada = hoje > p["vencimento"]
    juros = (D(p["valor"]) * D("0.0033") * (hoje - p["vencimento"]).days).quantize(D("0.01")) if atrasada else D(0)
    total = D(p["valor"]) + juros
    conta = conta_srv.conta_do_cliente(con, cliente_id)
    t = conta_srv.lancar(con, conta["id"], "pagamento_parcela", "saida", total,
                         f"Parcela {p['numero_parcela']} do empréstimo", categoria="Contas e serviços",
                         contraparte_nome="Vértis Crédito")
    executar(con, """UPDATE parcelas_emprestimo SET valor_pago=%s, pago_em=%s, juros_atraso=%s, status=%s,
                            transacao_id=%s WHERE id=%s""",
             (total, relogio.agora(), juros, "paga_atrasada" if atrasada else "paga", t["id"], parcela_id))
    executar(con, "UPDATE contratos_emprestimo SET saldo_devedor = GREATEST(0, saldo_devedor - %s) WHERE id=%s",
             (p["valor"], p["contrato"]))
    if not consultar_um(con, """SELECT id FROM parcelas_emprestimo WHERE contrato_id=%s
                                 AND status NOT IN ('paga','paga_atrasada') LIMIT 1""", (p["contrato"],)):
        executar(con, "UPDATE contratos_emprestimo SET status='quitado', quitado_em=%s WHERE id=%s",
                 (relogio.agora(), p["contrato"]))
    efeitos = eventos.registrar(con, cliente_id, "parcela_paga", "emprestimo", parcela_id, total,
                                impacto="neutro" if atrasada else "positivo")
    return {"valor_pago": float(total), "atrasada": atrasada, "efeitos": efeitos}


def contratos(con, cliente_id):
    lista = consultar(con, """SELECT c.*, p.taxa_juros_mensal, p.num_parcelas, p.valor_parcela
                                FROM contratos_emprestimo c JOIN propostas_emprestimo p ON p.id = c.proposta_id
                               WHERE c.cliente_id=%s ORDER BY c.assinado_em DESC""", (cliente_id,))
    for c in lista:
        c["parcelas"] = consultar(con, """SELECT id, numero_parcela, valor, vencimento, status, pago_em
                                           FROM parcelas_emprestimo WHERE contrato_id=%s ORDER BY numero_parcela""",
                                  (c["id"],))
    return lista
