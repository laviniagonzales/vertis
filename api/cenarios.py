"""
CENÁRIOS PARA A APRESENTAÇÃO — o problema sendo resolvido, com números
=====================================================================
Roda pessoas do público-alvo (pouco ou nenhum histórico, baixa renda)
pelas MESMAS regras de negócio da API, mês a mês, e mostra a evolução
do limite e do score.

Nada é gravado: tudo roda dentro de UMA transação que é desfeita
(ROLLBACK) no final, e o relógio da simulação volta para onde estava.

Como rodar (pasta api, com o MySQL ligado):
    python cenarios.py              → tabela no terminal
    python cenarios.py --json x.json → também salva os números em JSON
"""
import json
import sys
from decimal import Decimal

import relogio
from db import conexao, consultar_um
from servicos import clientes, credito, metas, open_finance, seguranca, simulacao

MESES = 12

# comportamento por mês: "em_dia" ou "atrasa"
PERSONAS = [
    {"chave": "ana", "nome": "Ana Souza", "idade": "diarista, 34 anos", "renda": 1400, "tipo": "informal",
     "ocupacao": "Diarista", "historia": "Nunca teve cartão. Banco tradicional recusou por falta de histórico.",
     "plano": ["em_dia"] * MESES, "open_finance_mes": None},
    {"chave": "gabriel", "nome": "Gabriel Silva", "idade": "entregador, 22 anos", "renda": 2500, "tipo": "informal",
     "ocupacao": "Entregador por aplicativo", "historia": "Renda informal, sem holerite: não consegue comprovar renda.",
     "plano": ["em_dia"] * MESES, "open_finance_mes": None},
    {"chave": "jonas", "nome": "Jonas Lima", "idade": "jovem aprendiz, 19 anos", "renda": 1100, "tipo": "formal",
     "ocupacao": "Jovem aprendiz", "historia": "Primeiro emprego. Tem conta em outro banco e autoriza o Open Finance.",
     "plano": ["em_dia"] * MESES, "open_finance_mes": 2},
    {"chave": "carla", "nome": "Carla Mendes", "idade": "vendedora autônoma, 41 anos", "renda": 1800,
     "tipo": "autonomo", "ocupacao": "Vendedora autônoma",
     "historia": "Atrasa duas faturas no início: o sistema freia o limite e depois ela se recupera.",
     "plano": ["em_dia", "atrasa", "atrasa"] + ["em_dia"] * (MESES - 3), "open_finance_mes": None},
]


def _cadastrar(con, p, n):
    cpf = seguranca.gerar_cpf_valido(987_654_000 + n * 13 + 7)
    r = clientes.cadastrar(con, {
        "nome_completo": p["nome"], "cpf": cpf, "data_nascimento": "1995-06-10",
        "email": f"{p['chave']}.cenario{n}@demo.vertis.com", "telefone": "11999990000",
        "renda_mensal_declarada": p["renda"], "ocupacao": p["ocupacao"], "tipo_renda": p["tipo"],
        "senha": "123456",
        "consentimentos": {"analise_credito": True, "uso_dados_comportamentais": True,
                           "marketing": False, "compartilhamento_parceiros": False},
    })
    metas.criar(con, r["cliente_id"], "Reserva de emergência", 1000)
    clientes.registrar_acesso(con, r["cliente_id"])
    return r["cliente_id"]


def _foto(con, cid, mes, comportamento=None):
    lim = consultar_um(con, "SELECT limite_total, limite_utilizado FROM limites_credito WHERE cliente_id=%s", (cid,))
    perfil = consultar_um(con, """SELECT faturas_pagas_em_dia, faturas_atrasadas, renda_media_comprovada
                                  FROM perfil_financeiro WHERE cliente_id=%s""", (cid,))
    saldo = consultar_um(con, "SELECT saldo_disponivel FROM contas WHERE cliente_id=%s", (cid,))
    s = credito.ultimo_score(con, cid)
    return {"mes": mes, "comportamento": comportamento, "limite": float(lim["limite_total"]),
            "utilizado": float(lim["limite_utilizado"]), "score": s["score_interno"],
            "risco": credito.risco_por_score(s["score_interno"]),
            "faturas_em_dia": perfil["faturas_pagas_em_dia"] if perfil else 0,
            "faturas_atrasadas": perfil["faturas_atrasadas"] if perfil else 0,
            "renda_comprovada": float(perfil["renda_media_comprovada"] or 0) if perfil else 0,
            "saldo_conta": float(saldo["saldo_disponivel"])}


def rodar():
    deslocamento_original = relogio.deslocamento_dias()
    resultado = []
    try:
        with conexao() as con:
            inst = consultar_um(con, "SELECT id FROM instituicoes_financeiras ORDER BY nome LIMIT 1")
            for n, p in enumerate(PERSONAS):
                relogio.resetar()                         # cada pessoa começa "hoje"
                cid = _cadastrar(con, p, n)
                linhas = [_foto(con, cid, 0)]
                for mes in range(1, MESES + 1):
                    if p["open_finance_mes"] == mes and inst:
                        open_finance.conectar(con, cid, inst["id"])
                    comp = p["plano"][mes - 1]
                    simulacao.simular_mes(con, cid, comportamento=comp)
                    linhas.append(_foto(con, cid, mes, comp))
                resultado.append({**{k: v for k, v in p.items() if k != "plano"}, "meses": linhas})
                print(f"  ok: {p['nome']}", file=sys.stderr, flush=True)
            con.rollback()                                 # desfaz TUDO: o banco fica como estava
    finally:
        relogio._gravar_deslocamento(deslocamento_original)
    return resultado


def _reais(v):
    return "R$ " + f"{v:,.0f}".replace(",", ".")


def imprimir(resultado):
    for p in resultado:
        print(f"\n{p['nome']} ({p['idade']}) — renda {_reais(p['renda'])} ({p['tipo']})")
        print(f"  {p['historia']}")
        print("  mês  pagou     limite     score  risco        em dia  atrasos")
        for m in p["meses"]:
            print(f"  {m['mes']:>3}  {(m['comportamento'] or '-'):<8} {_reais(m['limite']):>9}  {m['score']:>5}  "
                  f"{m['risco']:<12} {m['faturas_em_dia']:>5}  {m['faturas_atrasadas']:>6}")
        ini, fim = p["meses"][0], p["meses"][-1]
        print(f"  → limite {_reais(ini['limite'])} → {_reais(fim['limite'])} "
              f"({fim['limite'] / p['renda']:.1f}x a renda) • score {ini['score']} → {fim['score']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dados = rodar()
    imprimir(dados)
    if "--json" in sys.argv:
        caminho = sys.argv[sys.argv.index("--json") + 1]
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
