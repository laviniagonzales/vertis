"""
ACESSO AO BANCO DE DADOS
========================
Aqui ficam as funções que conversam com o MySQL. Todo o resto da API
usa só estas funções, então se um dia trocarmos de banco, mexemos aqui.

Conceito importante: TRANSAÇÃO DE BANCO
  Uma operação como "pagar fatura" mexe em várias tabelas (conta,
  transações, fatura, limite...). Ou TUDO dá certo, ou NADA é gravado.
  Por isso usamos `with conexao() as con:` — se der erro no meio,
  o rollback desfaz tudo automaticamente.
"""
import json
import uuid
from contextlib import contextmanager

import pymysql
import pymysql.cursors

import config


@contextmanager
def conexao():
    """Abre uma conexão, entrega para quem pediu e fecha no final.
    Se tudo correu bem: COMMIT (grava). Se deu erro: ROLLBACK (desfaz)."""
    con = pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORTA,
        user=config.DB_USUARIO,
        password=config.DB_SENHA,
        database=config.DB_NOME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,  # cada linha vira um dicionário
        autocommit=False,
    )
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def novo_id() -> str:
    """Gera um UUID (identificador único universal), como pede o roteiro."""
    return str(uuid.uuid4())


def consultar(con, sql: str, params=None) -> list[dict]:
    """Executa um SELECT e devolve uma lista de linhas (dicionários)."""
    with con.cursor() as cur:
        cur.execute(sql, params or ())
        return list(cur.fetchall())


def consultar_um(con, sql: str, params=None) -> dict | None:
    """Executa um SELECT e devolve só a primeira linha (ou None)."""
    with con.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def executar(con, sql: str, params=None) -> int:
    """Executa UPDATE/DELETE/INSERT e devolve quantas linhas foram afetadas."""
    with con.cursor() as cur:
        return cur.execute(sql, params or ())


def inserir(con, tabela: str, dados: dict) -> str:
    """Insere uma linha em `tabela` e devolve o id gerado.

    Exemplo: inserir(con, "contas", {"cliente_id": "...", "numero_conta": "123"})
    vira:    INSERT INTO contas (id, cliente_id, numero_conta) VALUES (%s, %s, %s)
    Os %s são preenchidos pelo PyMySQL de forma segura (evita SQL Injection).
    """
    dados = dict(dados)
    dados.setdefault("id", novo_id())
    for chave, valor in dados.items():          # dicionários/listas viram JSON
        if isinstance(valor, (dict, list)):
            dados[chave] = json.dumps(valor, ensure_ascii=False)
    colunas = ", ".join(dados.keys())
    marcadores = ", ".join(["%s"] * len(dados))
    executar(con, f"INSERT INTO {tabela} ({colunas}) VALUES ({marcadores})", tuple(dados.values()))
    return dados["id"]


def auditar(con, acao: str, tabela: str | None, registro_id: str | None,
            antes=None, depois=None, ator_tipo="sistema", ator_id=None, ip=None):
    """Grava um registro em logs_auditoria ("quem fez o quê e quando")."""
    def _limpo(v):
        return json.loads(json.dumps(v, default=str)) if v is not None else None

    inserir(con, "logs_auditoria", {
        "ator_tipo": ator_tipo, "ator_id": ator_id, "acao": acao,
        "tabela_afetada": tabela, "registro_id": registro_id,
        "valores_antes": _limpo(antes), "valores_depois": _limpo(depois), "ip": ip,
    })
