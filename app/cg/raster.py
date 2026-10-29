"""
RASTERIZAÇÃO, ANTIALIASING E TONALIZAÇÃO — o nosso próprio "pintor de pixels"
============================================================================
Conteúdo da disciplina: rasterização, técnicas de antisserrilhado,
tonalização (interpolação de cores), curvas.

RASTERIZAR = transformar uma forma matemática (linha, curva, anel) em
PIXELS. Aqui fazemos isso "na mão" com NumPy: para cada pixel calculamos
a DISTÂNCIA até a forma e decidimos a cor dele.

  • SEM antialiasing: o pixel é pintado se d <= espessura/2   → borda em "escada"
  • COM antialiasing: o pixel recebe uma COBERTURA entre 0 e 1
      cobertura = espessura/2 − d + 0,5    (limitada entre 0 e 1)
    Pixels da borda ficam semitransparentes → a borda parece lisa.

O resultado é uma matriz (altura × largura × 4 canais RGBA) que vira
uma TEXTURA e é desenhada na tela.
"""
import math

import numpy as np


# =====================================================================
# Curvas (pontos e vetores)
# =====================================================================
def bezier_cubica(p0, p1, p2, p3, n=24) -> np.ndarray:
    """B(t) = (1−t)³P0 + 3(1−t)²tP1 + 3(1−t)t²P2 + t³P3,  t de 0 a 1"""
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.asarray, (p0, p1, p2, p3))
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * (t ** 2) * p2 + (t ** 3) * p3


def curva_suave(pontos, n_por_trecho=20) -> np.ndarray:
    """Passa uma curva SUAVE por todos os pontos (Catmull-Rom convertida em Bézier).
    Os pontos de controle vêm dos VETORES entre os pontos vizinhos."""
    p = np.asarray(pontos, dtype=float)
    if len(p) < 2:
        return p
    estendidos = np.vstack([p[0] - (p[1] - p[0]), p, p[-1] + (p[-1] - p[-2])])
    saida = []
    for i in range(1, len(estendidos) - 2):
        a, b, c, d = estendidos[i - 1], estendidos[i], estendidos[i + 1], estendidos[i + 2]
        c1 = b + (c - a) / 6          # vetor tangente em b
        c2 = c - (d - b) / 6          # vetor tangente em c
        trecho = bezier_cubica(b, c1, c2, c, n_por_trecho)
        saida.append(trecho if not saida else trecho[1:])
    return np.vstack(saida)


# =====================================================================
# Cores
# =====================================================================
def hex_rgb(cor: str) -> np.ndarray:
    cor = cor.lstrip("#")
    return np.array([int(cor[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def interpolar_cores(paradas, t: np.ndarray) -> np.ndarray:
    """Interpolação LINEAR entre várias cores (t de 0 a 1) — a base do Gouraud shading."""
    paradas = [hex_rgb(c) if isinstance(c, str) else np.asarray(c) for c in paradas]
    t = np.clip(t, 0, 1) * (len(paradas) - 1)
    i = np.minimum(t.astype(int), len(paradas) - 2)
    f = (t - i)[..., None]
    a = np.stack(paradas)[i]
    b = np.stack(paradas)[i + 1]
    return a * (1 - f) + b * f


def _para_uint8(rgb, alfa) -> np.ndarray:
    rgba = np.concatenate([rgb, alfa[..., None]], axis=-1)
    return (np.clip(rgba, 0, 1) * 255).astype(np.uint8)


# =====================================================================
# Rasterização de uma linha grossa com várias partes (polilinha)
# =====================================================================
def rasterizar_polilinha(pontos, largura: int, altura: int, espessura: float, cores,
                         antialias=True, brilho=0.0) -> np.ndarray:
    """Desenha a polilinha numa imagem RGBA. A cor varia ao longo da linha.
    brilho > 0 adiciona um "glow" (halo) em volta — luz que se espalha."""
    pts = np.asarray(pontos, dtype=float)
    yy, xx = np.mgrid[0:altura, 0:largura].astype(float) + 0.5    # centro de cada pixel
    distancia = np.full((altura, largura), np.inf)
    posicao = np.zeros((altura, largura))                          # 0 = começo da linha, 1 = fim

    comprimentos = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    acumulado = np.concatenate([[0], np.cumsum(comprimentos)])
    total = max(acumulado[-1], 1e-9)
    alcance = espessura / 2 + 1 + (espessura * 3 if brilho else 0)

    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        # só olhamos os pixels perto do segmento (caixa envolvente) — mais rápido
        x0 = int(max(0, min(a[0], b[0]) - alcance)); x1 = int(min(largura, max(a[0], b[0]) + alcance + 1))
        y0 = int(max(0, min(a[1], b[1]) - alcance)); y1 = int(min(altura, max(a[1], b[1]) + alcance + 1))
        if x0 >= x1 or y0 >= y1:
            continue
        px, py = xx[y0:y1, x0:x1], yy[y0:y1, x0:x1]
        ab = b - a
        l2 = max(ab @ ab, 1e-9)
        # projeção do pixel P sobre o segmento AB:  t = (P−A)·AB / |AB|²
        t = np.clip(((px - a[0]) * ab[0] + (py - a[1]) * ab[1]) / l2, 0, 1)
        d = np.hypot(px - (a[0] + t * ab[0]), py - (a[1] + t * ab[1]))
        menor = d < distancia[y0:y1, x0:x1]
        distancia[y0:y1, x0:x1] = np.where(menor, d, distancia[y0:y1, x0:x1])
        posicao[y0:y1, x0:x1] = np.where(menor, (acumulado[i] + t * math.sqrt(l2)) / total,
                                          posicao[y0:y1, x0:x1])

    if antialias:
        cobertura = np.clip(espessura / 2 - distancia + 0.5, 0, 1)
    else:
        cobertura = (distancia <= espessura / 2).astype(float)

    cor = interpolar_cores(cores, posicao)
    alfa = cobertura
    if brilho:
        halo = np.exp(-(distancia / (espessura * 1.6)) ** 2) * brilho
        alfa = np.maximum(alfa, halo)
        cor = cor * (cobertura[..., None] + (1 - cobertura[..., None]) * 0.9)
    return _para_uint8(cor, alfa)


# =====================================================================
# Anel (gráfico do crédito progressivo / medidor do score)
# =====================================================================
def rasterizar_anel(tamanho: int, espessura: float, fracao: float, cor_fundo, cores_arco,
                    antialias=True, inicio_graus=90.0, abertura_graus=360.0) -> np.ndarray:
    """Anel com uma parte "cheia" (fracao de 0 a 1) começando no topo, sentido horário."""
    c = tamanho / 2
    raio = c - espessura / 2 - 1
    yy, xx = np.mgrid[0:tamanho, 0:tamanho].astype(float) + 0.5
    dx, dy = xx - c, yy - c
    d = np.abs(np.hypot(dx, dy) - raio)                         # distância até o círculo central do anel
    angulo = (inicio_graus - np.degrees(np.arctan2(dy, dx))) % 360   # 0° no início, crescendo no sentido horário
    dentro_abertura = angulo <= abertura_graus
    cobertura = np.clip(espessura / 2 - d + 0.5, 0, 1) if antialias else (d <= espessura / 2).astype(float)
    cobertura = cobertura * dentro_abertura

    t = angulo / max(abertura_graus, 1e-9)
    cheio = t <= fracao
    cor = np.where(cheio[..., None], interpolar_cores(cores_arco, t / max(fracao, 1e-9)),
                   np.broadcast_to(hex_rgb(cor_fundo) if isinstance(cor_fundo, str) else cor_fundo, (tamanho, tamanho, 3)))
    alfa = cobertura * np.where(cheio, 1.0, 0.35)
    return _para_uint8(cor, alfa)


# =====================================================================
# Fundos com degradê (tonalização)
# =====================================================================
def gradiente_vertical(largura: int, altura: int, cores) -> np.ndarray:
    """cores[0] embaixo → cores[-1] em cima."""
    t = np.linspace(0, 1, altura)[:, None].repeat(largura, axis=1)
    return _para_uint8(interpolar_cores(cores, t), np.ones((altura, largura)))


def gradiente_diagonal(largura: int, altura: int, cores) -> np.ndarray:
    yy, xx = np.mgrid[0:altura, 0:largura].astype(float)
    t = (xx / max(largura - 1, 1) * 0.6 + yy / max(altura - 1, 1) * 0.4)
    return _para_uint8(interpolar_cores(cores, t), np.ones((altura, largura)))


def esfera_iluminada(tamanho: int, cor_base, luz=(-0.5, 0.6, 0.7), brilho_especular=0.8) -> np.ndarray:
    """Medalha 'esférica' com iluminação de PHONG calculada por pixel:
        intensidade = ambiente + difusa·(N·L) + especular·(R·V)^n
    N = normal da esfera naquele pixel, L = direção da luz, V = direção do olho."""
    c = tamanho / 2
    yy, xx = np.mgrid[0:tamanho, 0:tamanho].astype(float) + 0.5
    nx, ny = (xx - c) / c, (yy - c) / c
    r2 = nx ** 2 + ny ** 2
    dentro = r2 <= 1
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    L = np.asarray(luz) / np.linalg.norm(luz)
    ndotl = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    # vetor refletido R = 2(N·L)N − L ; olho em V = (0, 0, 1) → R·V = Rz
    rz = 2 * ndotl * nz - L[2]
    especular = np.clip(rz, 0, 1) ** 24 * brilho_especular
    base = hex_rgb(cor_base) if isinstance(cor_base, str) else np.asarray(cor_base)
    cor = base * (0.35 + 0.75 * ndotl)[..., None] + especular[..., None]
    borda = np.clip((1 - np.sqrt(r2)) * c, 0, 1)                 # antialiasing da borda do círculo
    return _para_uint8(cor, borda * dentro)


# =====================================================================
# Para o Laboratório: grade de pixels ampliada
# =====================================================================
def bresenham(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    """Algoritmo clássico de rasterização de linhas: só usa números inteiros.
    Cada pixel ou está 100% aceso ou 100% apagado → serrilhado."""
    pixels = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    erro = dx + dy
    while True:
        pixels.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pixels
        e2 = 2 * erro
        if e2 >= dy:
            erro += dy
            x0 += sx
        if e2 <= dx:
            erro += dx
            y0 += sy


def cobertura_linha(colunas: int, linhas: int, x0, y0, x1, y1, espessura=1.0, amostras=4) -> np.ndarray:
    """ANTIALIASING POR SUPERAMOSTRAGEM: cada pixel é dividido em amostras×amostras
    subpixels; a cobertura é a fração dos subpixels que caem dentro da linha."""
    sub = (np.arange(amostras) + 0.5) / amostras
    yy, xx = np.mgrid[0:linhas, 0:colunas].astype(float)
    total = np.zeros((linhas, colunas))
    a, b = np.array([x0, y0], float), np.array([x1, y1], float)
    ab = b - a
    l2 = max(ab @ ab, 1e-9)
    for sy in sub:
        for sx in sub:
            px, py = xx + sx, yy + sy
            t = np.clip(((px - a[0]) * ab[0] + (py - a[1]) * ab[1]) / l2, 0, 1)
            d = np.hypot(px - (a[0] + t * ab[0]), py - (a[1] + t * ab[1]))
            total += d <= espessura / 2
    return total / (amostras * amostras)


# =====================================================================
# Ponte com o Kivy: matriz NumPy → textura
# =====================================================================
def para_textura(imagem: np.ndarray, filtro_suave=True):
    from kivy.graphics.texture import Texture
    altura, largura = imagem.shape[:2]
    tex = Texture.create(size=(largura, altura), colorfmt="rgba")
    tex.blit_buffer(np.ascontiguousarray(imagem).tobytes(), colorfmt="rgba", bufferfmt="ubyte")
    if not filtro_suave:
        tex.mag_filter = "nearest"   # mostra os pixels "quadradões" (útil no laboratório)
        tex.min_filter = "nearest"
    return tex
