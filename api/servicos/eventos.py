"""
EVENTOS COMPORTAMENTAIS — o "ponto de encontro" da Vértis
========================================================
Toda ação relevante do cliente vira um EVENTO. Cada evento segue por
DUAS TRILHAS (seção 10 do roteiro do banco):

     ação do cliente (ex.: pagou a fatura em dia)
                     │
          eventos_comportamentais
           ┌─────────┴──────────┐
   TRILHA 1: CRÉDITO      TRILHA 2: GAMIFICAÇÃO
   perfil → score →       XP, pontos, milhas →
   limite                 nível → conquistas → benefícios
"""
from decimal import Decimal

from db import inserir
import relogio
from servicos import credito, gamificacao

# Cada tipo de evento tem um impacto fixo no perfil do cliente
IMPACTO = {
    "fatura_paga_em_dia": "positivo",
    "fatura_atrasada": "negativo",
    "deposito_recebido": "positivo",
    "salario_recebido": "positivo",
    "compra_realizada": "neutro",
    "acesso_app": "neutro",
    "meta_atingida": "positivo",
    "open_finance_conectado": "positivo",
    "parcela_paga": "positivo",
    "saldo_negativo": "negativo",
}

# Eventos que disparam uma revisão do limite de crédito
EVENTOS_QUE_REVISAM_LIMITE = {"fatura_paga_em_dia", "fatura_atrasada", "open_finance_conectado"}


def registrar(con, cliente_id: str, tipo_evento: str, origem: str,
              referencia_id: str | None = None, valor=None, dados_extras: dict | None = None,
              impacto: str | None = None) -> dict:
    """Registra o evento e processa as duas trilhas. Devolve um resumo do que aconteceu."""
    evento = {
        "cliente_id": cliente_id,
        "tipo_evento": tipo_evento,
        "origem": origem,
        "referencia_id": referencia_id,
        "valor": Decimal(str(valor)) if valor is not None else None,
        "impacto": impacto or IMPACTO[tipo_evento],
        "dados_extras": dados_extras,
        "ocorrido_em": relogio.agora(),
    }
    evento["id"] = inserir(con, "eventos_comportamentais", evento)

    # TRILHA 2 — gamificação (XP, pontos, milhas, nível, conquistas)
    recompensas = gamificacao.processar_evento(con, evento)

    # TRILHA 1 — crédito (perfil → score → limite)
    credito.atualizar_perfil(con, cliente_id)
    score = credito.calcular_score(con, cliente_id)
    mudanca_limite = None
    if tipo_evento in EVENTOS_QUE_REVISAM_LIMITE:
        mudanca_limite = credito.revisar_limite(con, cliente_id, gatilho=tipo_evento)

    return {"evento_id": evento["id"], "recompensas": recompensas,
            "score": score["score_interno"], "limite": mudanca_limite}
