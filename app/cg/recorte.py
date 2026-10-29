"""
RECORTE (CLIPPING) — algoritmo de Cohen–Sutherland
==================================================
Conteúdo da disciplina: recorte e visibilidade.

Problema: só podemos desenhar o que está DENTRO da janela de recorte.
Ideia: cada ponta da linha ganha um CÓDIGO DE 4 BITS dizendo onde ela está:

        1001 | 1000 | 1010            bit 1 (8) = acima
        -----+------+-----            bit 2 (4) = abaixo
        0001 | 0000 | 0010            bit 3 (2) = à direita
        -----+------+-----            bit 4 (1) = à esquerda
        0101 | 0100 | 0110

  • código1 OR  código2 == 0  → linha toda dentro: aceita
  • código1 AND código2 != 0 → as duas pontas do mesmo lado de fora: descarta
  • senão                     → corta a linha na borda e testa de novo

Onde usamos no app: a "trilha de ascensão" é recortada para caber no
painel, e o Laboratório de CG mostra o algoritmo funcionando ao vivo.
"""

DENTRO, ESQUERDA, DIREITA, ABAIXO, ACIMA = 0, 1, 2, 4, 8


def codigo_regiao(x, y, xmin, ymin, xmax, ymax) -> int:
    codigo = DENTRO
    if x < xmin:
        codigo |= ESQUERDA
    elif x > xmax:
        codigo |= DIREITA
    if y < ymin:
        codigo |= ABAIXO
    elif y > ymax:
        codigo |= ACIMA
    return codigo


def cohen_sutherland(x0, y0, x1, y1, xmin, ymin, xmax, ymax):
    """Devolve a parte visível da linha (x0, y0, x1, y1) ou None se for invisível."""
    c0 = codigo_regiao(x0, y0, xmin, ymin, xmax, ymax)
    c1 = codigo_regiao(x1, y1, xmin, ymin, xmax, ymax)
    while True:
        if not (c0 | c1):          # as duas pontas dentro
            return x0, y0, x1, y1
        if c0 & c1:                # as duas fora, do mesmo lado
            return None
        fora = c0 or c1            # escolhe a ponta que está fora
        if fora & ACIMA:
            x, y = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0), ymax
        elif fora & ABAIXO:
            x, y = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0), ymin
        elif fora & DIREITA:
            x, y = xmax, y0 + (y1 - y0) * (xmax - x0) / (x1 - x0)
        else:
            x, y = xmin, y0 + (y1 - y0) * (xmin - x0) / (x1 - x0)
        if fora == c0:
            x0, y0 = x, y
            c0 = codigo_regiao(x0, y0, xmin, ymin, xmax, ymax)
        else:
            x1, y1 = x, y
            c1 = codigo_regiao(x1, y1, xmin, ymin, xmax, ymax)


def recortar_polilinha(pontos, xmin, ymin, xmax, ymax) -> list[list[tuple]]:
    """Recorta uma linha com vários segmentos. Devolve os trechos visíveis."""
    trechos, atual = [], []
    for (x0, y0), (x1, y1) in zip(pontos, pontos[1:]):
        r = cohen_sutherland(x0, y0, x1, y1, xmin, ymin, xmax, ymax)
        if r is None:
            if atual:
                trechos.append(atual)
                atual = []
            continue
        a, b = (r[0], r[1]), (r[2], r[3])
        if not atual:
            atual = [a]
        elif atual[-1] != a:
            trechos.append(atual)
            atual = [a]
        atual.append(b)
        if (r[2], r[3]) != (x1, y1):   # saiu da janela no meio do segmento
            trechos.append(atual)
            atual = []
    if atual:
        trechos.append(atual)
    return trechos
