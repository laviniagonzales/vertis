"""
RELÓGIO DA SIMULAÇÃO
====================
O crédito progressivo depende do TEMPO: faturas fecham, vencem, o
limite é revisto a cada mês... Na apresentação não dá para esperar
6 meses! Então a API usa este relógio no lugar do relógio do computador.

- Em uso normal, ele marca a hora real (deslocamento = 0 dias).
- No "modo demonstração", avançamos o relógio dia a dia para simular
  meses de uso em poucos segundos.

O deslocamento fica salvo no arquivo relogio.json.
Datas e horas são guardadas em UTC, como pede o roteiro do banco.
"""
import json
import os
from datetime import datetime, timedelta, timezone

_ARQUIVO = os.path.join(os.path.dirname(__file__), "relogio.json")


def _ler_deslocamento() -> float:
    try:
        with open(_ARQUIVO, encoding="utf-8") as f:
            return float(json.load(f).get("dias", 0))
    except (FileNotFoundError, ValueError):
        return 0.0


def _gravar_deslocamento(dias: float):
    with open(_ARQUIVO, "w", encoding="utf-8") as f:
        json.dump({"dias": dias}, f)


def agora() -> datetime:
    """Data e hora atual (UTC) + deslocamento da simulação."""
    real = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    return real + timedelta(days=_ler_deslocamento())


def hoje():
    return agora().date()


def avancar(dias: float = 1):
    _gravar_deslocamento(_ler_deslocamento() + dias)


def resetar():
    _gravar_deslocamento(0)


def deslocamento_dias() -> float:
    return _ler_deslocamento()
