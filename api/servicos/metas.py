"""
GESTÃO FINANCEIRA: METAS (módulo 8)
==================================
O cliente cria uma meta (ex.: Reserva de emergência) e faz aportes.
O dinheiro sai do saldo disponível e fica "guardado" na meta.
Quando o valor atual alcança o alvo → evento 'meta_atingida' (pontos!).
"""
from decimal import Decimal

import relogio
from db import consultar, consultar_um, executar, inserir
from servicos import conta as conta_srv, eventos

D = Decimal


def criar(con, cliente_id, nome, valor_alvo, data_alvo=None, aporte_automatico=None):
    return inserir(con, "metas_financeiras", {"cliente_id": cliente_id, "nome": nome, "valor_alvo": D(str(valor_alvo)),
                                              "data_alvo": data_alvo, "aporte_automatico": aporte_automatico})


def listar(con, cliente_id):
    return consultar(con, "SELECT * FROM metas_financeiras WHERE cliente_id=%s ORDER BY criado_em", (cliente_id,))


def aportar(con, cliente_id, meta_id, valor) -> dict:
    meta = consultar_um(con, "SELECT * FROM metas_financeiras WHERE id=%s AND cliente_id=%s FOR UPDATE",
                        (meta_id, cliente_id))
    if not meta or meta["status"] != "ativa":
        raise ValueError("Meta indisponível")
    valor = D(str(valor))
    conta = conta_srv.conta_do_cliente(con, cliente_id)
    conta_srv.lancar(con, conta["id"], "ted", "saida", valor, f"Guardado na meta: {meta['nome']}",
                     categoria="Transferências", contraparte_nome="Vértis Metas")
    novo = D(meta["valor_atual"]) + valor
    atingiu = novo >= D(meta["valor_alvo"])
    executar(con, "UPDATE metas_financeiras SET valor_atual=%s, status=%s, concluida_em=%s WHERE id=%s",
             (novo, "concluida" if atingiu else "ativa", relogio.agora() if atingiu else None, meta_id))
    efeitos = eventos.registrar(con, cliente_id, "meta_atingida", "app", meta_id, novo) if atingiu else None
    return {"valor_atual": float(novo), "atingida": atingiu, "efeitos": efeitos}
