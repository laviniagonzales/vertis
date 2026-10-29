"""
NOTIFICAÇÕES
============
Toda novidade importante (limite subiu, conquista, nível novo...) vira
uma linha em `notificacoes`. O app lê as não lidas e mostra a animação.
"""
from db import inserir, consultar, executar
import relogio


def notificar(con, cliente_id, tipo, titulo, mensagem, referencia_id=None, canal="app"):
    return inserir(con, "notificacoes", {
        "cliente_id": cliente_id, "tipo": tipo, "canal": canal,
        "titulo": titulo[:100], "mensagem": mensagem[:500],
        "referencia_id": referencia_id, "enviada_em": relogio.agora(),
    })


def listar(con, cliente_id, so_nao_lidas=False, limite=30):
    filtro = "AND lida = FALSE" if so_nao_lidas else ""
    return consultar(con, f"""
        SELECT id, tipo, titulo, mensagem, referencia_id, lida, enviada_em
          FROM notificacoes
         WHERE cliente_id = %s {filtro}
         ORDER BY enviada_em DESC, criado_em DESC
         LIMIT %s""", (cliente_id, limite))


def marcar_lidas(con, cliente_id, ids: list[str] | None = None):
    if ids:
        marcadores = ",".join(["%s"] * len(ids))
        executar(con, f"""UPDATE notificacoes SET lida = TRUE, lida_em = %s
                           WHERE cliente_id = %s AND id IN ({marcadores})""",
                 (relogio.agora(), cliente_id, *ids))
    else:
        executar(con, """UPDATE notificacoes SET lida = TRUE, lida_em = %s
                          WHERE cliente_id = %s AND lida = FALSE""",
                 (relogio.agora(), cliente_id))
