"""Cores da identidade visual da Vértis: branco, cinza e amarelo (visual de banco).

As CHAVES antigas (roxo, lilas, rosa, dourado...) foram mantidas para não quebrar
o código, mas agora apontam para a nova paleta:
  roxo / dourado / amarelo → amarelo da marca (botões principais e destaques)
  lilas / grafite          → cinza-grafite (contornos, ícones, detalhes)
  rosa                     → âmbar escuro (segunda cor dos degradês)
  dourado_claro            → dourado escuro (texto de destaque sobre o branco)
"""

CORES = {
    "fundo_base": "#F2F3F5",
    "fundo_topo": "#F8F9FA",
    "card": "#FFFFFF",
    "borda": "#E3E6EA",
    "amarelo": "#F5B700",
    "amarelo_suave": "#FFF5D1",
    "grafite": "#2B2F36",
    "cinza_claro": "#EEF0F3",
    "cinza_medio": "#C9CED6",
    "roxo": "#F5B700",
    "lilas": "#2B2F36",
    "rosa": "#D99A00",
    "dourado": "#F5B700",
    "dourado_claro": "#8A6400",
    "texto": "#1F2329",
    "texto2": "#6B7280",
    "verde": "#1E8E4E",
    "vermelho": "#D33A2C",
}

# Degradê da trilha de ascensão: cinza → amarelo → âmbar
CORES_TRILHA = ["#B8BEC7", "#F2C230", "#F5B700", "#D99A00"]

CORES_CATEGORIA = {
    "pagamento": "#1E8E4E", "uso": "#4B5563", "credito": "#F5B700",
    "viagem": "#D99A00", "educacao_financeira": "#0E7490",
}


def rgba(cor: str, alfa: float = 1.0) -> tuple:
    """'#F5B700' → (0.96, 0.72, 0.0, 1.0) — o formato que o Kivy usa."""
    cor = cor.lstrip("#")
    return tuple(int(cor[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (alfa,)
