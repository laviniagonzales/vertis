"""Cores da identidade visual da Vértis (inspiradas no mockup)."""

CORES = {
    "fundo_base": "#0F0824",
    "fundo_topo": "#2A1460",
    "card": "#22164A",
    "borda": "#3E2C7A",
    "roxo": "#8B5CF6",
    "lilas": "#A78BFA",
    "rosa": "#EC4899",
    "dourado": "#F5B83D",
    "dourado_claro": "#FFE29A",
    "texto": "#FFFFFF",
    "texto2": "#B9B3D6",
    "verde": "#34D399",
    "vermelho": "#F87171",
}

# Degradê da trilha de ascensão: roxo → rosa → dourado
CORES_TRILHA = ["#6D28D9", "#A855F7", "#EC4899", "#F5B83D"]

CORES_CATEGORIA = {
    "pagamento": "#34D399", "uso": "#60A5FA", "credito": "#A78BFA",
    "viagem": "#F5B83D", "educacao_financeira": "#F472B6",
}


def rgba(cor: str, alfa: float = 1.0) -> tuple:
    """'#8B5CF6' → (0.55, 0.36, 0.96, 1.0) — o formato que o Kivy usa."""
    cor = cor.lstrip("#")
    return tuple(int(cor[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (alfa,)
