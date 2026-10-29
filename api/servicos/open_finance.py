"""
OPEN FINANCE (módulo 6) — SIMULADO
=================================
No mundo real, o cliente é redirecionado ao outro banco, autoriza, e a
Vértis recebe os dados pela API regulada do Banco Central.
Aqui SIMULAMOS essa resposta: geramos contas e 3 meses de transações
"vindas" do outro banco. O resto do fluxo é igual ao real:
consentimento com prazo de 12 meses → importação sem duplicar
(id_externo) → renda recorrente → evento que acelera o limite.
"""
import random
from datetime import timedelta
from decimal import Decimal

import relogio
from db import consultar, consultar_um, executar, inserir
from servicos import eventos

D = Decimal


def instituicoes(con):
    return consultar(con, """SELECT id, nome, codigo_banco FROM instituicoes_financeiras
                              WHERE participa_open_finance = TRUE ORDER BY nome""")


def conectar(con, cliente_id, instituicao_id) -> dict:
    inst = consultar_um(con, "SELECT * FROM instituicoes_financeiras WHERE id=%s", (instituicao_id,))
    if not inst:
        raise ValueError("Instituição não encontrada")
    if consultar_um(con, """SELECT id FROM consentimentos_open_finance WHERE cliente_id=%s AND instituicao_id=%s
                             AND status='autorizado'""", (cliente_id, instituicao_id)):
        raise ValueError("Esta instituição já está conectada")

    agora = relogio.agora()
    consent_id = inserir(con, "consentimentos_open_finance", {
        "cliente_id": cliente_id, "instituicao_id": instituicao_id,
        "id_consentimento_externo": f"urn:{inst['codigo_banco']}:{random.getrandbits(64):016x}",
        "permissoes": ["CONTAS", "CARTOES", "TRANSACOES", "OPERACOES_CREDITO"],
        "status": "autorizado", "autorizado_em": agora, "expira_em": agora + timedelta(days=365),
        "ultima_sincronizacao_em": agora})

    # ---- dados "recebidos" do outro banco (determinísticos por cliente)
    rnd = random.Random(f"{cliente_id}{instituicao_id}")
    renda_extra = D(rnd.choice([600, 800, 1000, 1200]))
    conta_ext = inserir(con, "contas_externas", {
        "consentimento_id": consent_id, "tipo_produto": "conta_corrente",
        "identificador_externo": f"{inst['codigo_banco']}-{rnd.randint(10000, 99999)}",
        "saldo": D(rnd.randint(150, 900)), "atualizado_em": agora})
    inserir(con, "contas_externas", {
        "consentimento_id": consent_id, "tipo_produto": "cartao_credito",
        "identificador_externo": f"{inst['codigo_banco']}-CC-{rnd.randint(1000, 9999)}",
        "limite": D(rnd.choice([300, 500, 800])), "saldo_devedor": D(rnd.randint(50, 250)), "atualizado_em": agora})

    salario = consultar_um(con, "SELECT id FROM categorias WHERE nome='Salário' AND cliente_id IS NULL")["id"]
    alimentacao = consultar_um(con, "SELECT id FROM categorias WHERE nome='Alimentação' AND cliente_id IS NULL")["id"]
    for mes in range(3):
        quando = agora - timedelta(days=30 * mes + 5)
        inserir(con, "transacoes_externas", {
            "conta_externa_id": conta_ext, "id_externo": f"TX{mes}R{rnd.getrandbits(32):08x}", "tipo": "CREDITO",
            "direcao": "entrada", "valor": renda_extra, "descricao": "Renda extra (freelas)",
            "categoria_id": salario, "eh_renda_recorrente": True, "realizada_em": quando})
        for k in range(3):
            inserir(con, "transacoes_externas", {
                "conta_externa_id": conta_ext, "id_externo": f"TX{mes}D{k}{rnd.getrandbits(32):08x}",
                "tipo": "DEBITO", "direcao": "saida", "valor": D(rnd.randint(30, 160)),
                "descricao": rnd.choice(["Mercado", "Padaria", "Farmácia", "Transporte"]),
                "categoria_id": alimentacao, "realizada_em": quando + timedelta(days=k * 7)})

    efeitos = eventos.registrar(con, cliente_id, "open_finance_conectado", "open_finance", consent_id,
                                dados_extras={"instituicao": inst["nome"]})
    return {"consentimento_id": consent_id, "instituicao": inst["nome"],
            "renda_recorrente_encontrada": float(renda_extra), "efeitos": efeitos}


def revogar(con, cliente_id, consentimento_id):
    executar(con, """UPDATE consentimentos_open_finance SET status='revogado', revogado_em=%s
                      WHERE id=%s AND cliente_id=%s""", (relogio.agora(), consentimento_id, cliente_id))


def conexoes(con, cliente_id):
    return consultar(con, """SELECT co.id, i.nome AS instituicao, co.status, co.autorizado_em, co.expira_em
                               FROM consentimentos_open_finance co
                               JOIN instituicoes_financeiras i ON i.id = co.instituicao_id
                              WHERE co.cliente_id=%s ORDER BY co.criado_em DESC""", (cliente_id,))
