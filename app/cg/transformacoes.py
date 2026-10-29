"""
TRANSFORMAÇÕES GEOMÉTRICAS 2D e 3D (com coordenadas homogêneas)
===============================================================
Conteúdo da disciplina: pontos, vetores, matrizes, transformações 2D e 3D,
transformações projetivas.

POR QUE "HOMOGÊNEAS"?
  Um ponto 2D (x, y) vira (x, y, 1). Com essa coordenada extra, a
  TRANSLAÇÃO também vira uma multiplicação de matriz — e aí podemos
  JUNTAR várias transformações numa matriz só:

        M = T · R · S      (primeiro escala, depois gira, depois move)

  Atenção: a ordem importa! Lemos da direita para a esquerda.

Onde usamos no app:
  • avatar da trilha  → T · R · S  (move até o ponto, gira na direção da curva, pulsa)
  • moeda de pontos   → rotação 3D em Y + projeção
  • cartão 3D         → Rx · Ry + projeção em perspectiva
"""
import math

import numpy as np


# =====================================================================
# 2D  (matrizes 3x3)
# =====================================================================
def translacao2d(tx: float, ty: float) -> np.ndarray:
    """Move o objeto: x' = x + tx,  y' = y + ty"""
    return np.array([[1, 0, tx],
                     [0, 1, ty],
                     [0, 0, 1]], dtype=float)


def rotacao2d(angulo_rad: float) -> np.ndarray:
    """Gira em torno da origem:  x' = x·cosθ − y·senθ,  y' = x·senθ + y·cosθ"""
    c, s = math.cos(angulo_rad), math.sin(angulo_rad)
    return np.array([[c, -s, 0],
                     [s,  c, 0],
                     [0,  0, 1]], dtype=float)


def escala2d(sx: float, sy: float | None = None) -> np.ndarray:
    """Aumenta/diminui:  x' = x·sx,  y' = y·sy"""
    sy = sx if sy is None else sy
    return np.array([[sx, 0, 0],
                     [0, sy, 0],
                     [0,  0, 1]], dtype=float)


def compor(*matrizes: np.ndarray) -> np.ndarray:
    """compor(T, R, S) = T · R · S"""
    resultado = np.identity(matrizes[0].shape[0])
    for m in matrizes:
        resultado = resultado @ m
    return resultado


def aplicar2d(matriz: np.ndarray, pontos) -> np.ndarray:
    """Aplica a matriz 3x3 em uma lista de pontos [(x, y), ...]."""
    p = np.asarray(pontos, dtype=float)
    homogeneos = np.hstack([p, np.ones((len(p), 1))])      # (x, y) → (x, y, 1)
    transformados = homogeneos @ matriz.T
    return transformados[:, :2]


# =====================================================================
# 3D  (matrizes 4x4)
# =====================================================================
def translacao3d(tx, ty, tz) -> np.ndarray:
    m = np.identity(4)
    m[:3, 3] = [tx, ty, tz]
    return m


def escala3d(sx, sy=None, sz=None) -> np.ndarray:
    sy = sx if sy is None else sy
    sz = sx if sz is None else sz
    return np.diag([sx, sy, sz, 1.0])


def rotacao_x(a) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]], dtype=float)


def rotacao_y(a) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]], dtype=float)


def rotacao_z(a) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=float)


def perspectiva(distancia: float) -> np.ndarray:
    """PROJEÇÃO EM PERSPECTIVA (transformação projetiva).
    A câmera está no eixo Z, a `distancia` da origem, olhando para ela.
    A última linha faz  w = 1 − z/d.  Depois dividimos x e y por w:
    o que está mais LONGE (z negativo) fica MENOR — como no olho humano."""
    return np.array([[1, 0, 0, 0],
                     [0, 1, 0, 0],
                     [0, 0, 1, 0],
                     [0, 0, -1 / distancia, 1]], dtype=float)


def aplicar3d(matriz: np.ndarray, pontos) -> np.ndarray:
    """Aplica a matriz 4x4 em pontos [(x, y, z), ...] e devolve (x, y, z)."""
    p = np.asarray(pontos, dtype=float)
    h = np.hstack([p, np.ones((len(p), 1))]) @ matriz.T
    return h[:, :3]


def projetar(pontos3d, distancia: float) -> np.ndarray:
    """Projeta pontos 3D na tela: aplica a perspectiva e faz a DIVISÃO POR w."""
    p = np.asarray(pontos3d, dtype=float)
    h = np.hstack([p, np.ones((len(p), 1))]) @ perspectiva(distancia).T
    return h[:, :2] / h[:, 3:4]


def normal_da_face(p0, p1, p2) -> np.ndarray:
    """Vetor normal (perpendicular) de uma face = produto vetorial de duas arestas."""
    n = np.cross(np.subtract(p1, p0), np.subtract(p2, p0))
    tamanho = np.linalg.norm(n)
    return n / tamanho if tamanho else n


def normalizar(v) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    t = np.linalg.norm(v)
    return v / t if t else v


def formatar_matriz(m: np.ndarray) -> str:
    """Texto bonitinho da matriz (usado no Laboratório de CG)."""
    return "\n".join("[ " + "  ".join(f"{v:6.2f}" for v in linha) + " ]" for linha in m)
