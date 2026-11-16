"""
WIDGETS GRÁFICOS DA TELA DE EVOLUÇÃO
===================================
Cada widget usa os conceitos da disciplina (veja os comentários):

  TrilhaAscensao → curva de Bézier (vetores), recorte (Cohen–Sutherland),
                   rasterização com antialiasing, interpolação de cores,
                   avatar movido com T·S e seta girada com T·R·S
  MoedaGiratoria → objeto 3D (disco), rotação em Y, projeção, pintor, shading
  AnelCredito    → rasterização de anel com antialiasing
  Medalha        → iluminação de Phong por pixel (esfera)
"""
import math

import numpy as np
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Ellipse, Line, Mesh, Rectangle, InstructionGroup
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.widget import Widget
from kivy.animation import Animation

from cg import raster, recorte, transformacoes as tf
from tema import CORES, CORES_TRILHA, rgba


# ---------------------------------------------------------------- utilidades
def malha_poligono(pontos) -> Mesh:
    """Polígono convexo como 'leque de triângulos' (triangle_fan)."""
    vertices = []
    for x, y in pontos:
        vertices += [float(x), float(y), 0.0, 0.0]
    return Mesh(vertices=vertices, indices=list(range(len(pontos))), mode="triangle_fan")


def atualizar_malha(malha: Mesh, pontos):
    vertices = []
    for x, y in pontos:
        vertices += [float(x), float(y), 0.0, 0.0]
    malha.vertices = vertices
    malha.indices = list(range(len(pontos)))


def textura_texto(texto, tamanho=12, cor=(1, 1, 1, 1), negrito=False):
    rotulo = CoreLabel(text=texto, font_size=sp(tamanho), bold=negrito, color=cor)
    rotulo.refresh()
    return rotulo.texture


def circulo(cx, cy, r, n=18):
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], axis=1)


# =====================================================================
# Fundo com degradê (tonalização) — usado em todas as telas
# =====================================================================
class FundoGradiente(Widget):
    cores = ListProperty([CORES["fundo_base"], "#F5F6F8", CORES["fundo_topo"]])

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas:
            Color(1, 1, 1, 1)
            self._ret = Rectangle()
        self.bind(size=self._redesenhar, pos=self._redesenhar, cores=self._redesenhar)

    def _redesenhar(self, *_):
        # imagem pequena esticada: o filtro linear da placa de vídeo suaviza o degradê
        img = raster.gradiente_vertical(8, 128, self.cores)
        self._ret.texture = raster.para_textura(img)
        self._ret.pos, self._ret.size = self.pos, self.size


# =====================================================================
# Trilha de ascensão (o histórico do limite virando uma curva)
# =====================================================================
class TrilhaAscensao(Widget):
    valores = ListProperty([])         # histórico do limite (R$)
    previsto = NumericProperty(0)      # próximo limite previsto
    avanco = NumericProperty(0)        # 0 → 1 : animação do avatar subindo
    antialias = BooleanProperty(True)

    def __init__(self, **kw):
        super().__init__(**kw)
        self._t = 0.0
        self._curva_hist = None
        self._agendar = Clock.create_trigger(self._redesenhar, 0)
        self.bind(size=self._agendar, pos=self._agendar, valores=self._nova_trilha,
                  previsto=self._agendar, antialias=self._agendar, avanco=self._desenhar_avatar)
        self._grupo_avatar = InstructionGroup()
        self.canvas.after.add(self._grupo_avatar)
        Clock.schedule_interval(self._pulsar, 1 / 30)

    def _nova_trilha(self, *_):
        self._agendar()
        self.avanco = 0
        Animation(avanco=1, d=1.8, t="out_cubic").start(self)

    # ---- 1) PONTOS: cada valor do histórico vira um ponto (x, y) no painel
    def _pontos(self):
        w, h = self.size
        vals = list(self.valores) or [1]
        alvo = max(self.previsto or vals[-1], vals[-1])
        vmin, vmax = min(vals) * 0.8, max(alvo, max(vals)) * 1.02
        faixa = max(vmax - vmin, 1)

        def y(v):   # raiz quadrada: valores pequenos não ficam "esmagados" no fundo
            return h * 0.08 + math.sqrt(max(v - vmin, 0) / faixa) * h * 0.70

        n = len(vals)
        xs = [w * 0.10] if n == 1 else list(np.linspace(w * 0.06, w * 0.50, n))
        hist = [(x, y(v)) for x, v in zip(xs, vals)]
        futuro = (w * 0.62, max(y(alvo), hist[-1][1] + h * 0.06))
        return hist, futuro

    def _redesenhar(self, *_):
        if self.width < 10 or self.height < 10:
            return
        w, h = int(self.width), int(self.height)
        hist, futuro = self._pontos()

        # ---- 2) CURVA SUAVE (Bézier) passando pelos pontos
        k = 18
        curva = raster.curva_suave(hist + [futuro], k)
        corte = (len(hist) - 1) * (k - 1)
        curva_hist, curva_futuro = curva[:corte + 1], curva[corte:]
        if len(hist) == 1:
            curva_hist = np.array([hist[0], hist[0]])
        self._curva_hist = curva_hist

        # ---- 3) RECORTE: a curva pode "passar" da borda — Cohen–Sutherland corta
        m = dp(4)
        janela = (m, m, w - m, h - m)
        trechos = recorte.recortar_polilinha([tuple(p) for p in curva_hist], *janela)
        trechos_fut = recorte.recortar_polilinha([tuple(p) for p in curva_futuro], *janela)

        # ---- 4) RASTERIZAÇÃO com antialiasing + degradê de cores + brilho
        esp = dp(6)
        img = np.zeros((h, w, 4), np.uint8)
        for t in trechos:
            if len(t) > 1:
                img = np.maximum(img, raster.rasterizar_polilinha(t, w, h, esp, CORES_TRILHA[:3],
                                                                  self.antialias, brilho=0.55))
        img_fut = np.zeros((h, w, 4), np.uint8)
        for t in trechos_fut:                       # futuro: linha tracejada (pedaços alternados)
            for i in range(0, len(t) - 1, 6):
                pedaco = t[i:i + 4]
                if len(pedaco) > 1:
                    img_fut = np.maximum(img_fut, raster.rasterizar_polilinha(
                        pedaco, w, h, esp * 0.7, CORES_TRILHA[2:], self.antialias, brilho=0.4))

        self.canvas.clear()
        with self.canvas:
            Color(1, 1, 1, 0.55)
            Rectangle(texture=raster.para_textura(img_fut), pos=self.pos, size=(w, h))
            Color(1, 1, 1, 1)
            Rectangle(texture=raster.para_textura(img), pos=self.pos, size=(w, h))
            # nós da trilha (cada mudança de limite)
            for i, (px, py) in enumerate(hist):
                r = dp(5) if i < len(hist) - 1 else dp(7)
                Color(*rgba(CORES["dourado"] if i == len(hist) - 1 else CORES["cinza_medio"]))
                Ellipse(pos=(self.x + px - r, self.y + py - r), size=(2 * r, 2 * r))
                Color(1, 1, 1, 1)
                Ellipse(pos=(self.x + px - r / 2.4, self.y + py - r / 2.4), size=(r / 1.2, r / 1.2))
            # rótulos do primeiro e do último valor
            from servidor import reais_curto
            for (px, py), v in ((hist[0], self.valores[0] if self.valores else 0),):
                tex = textura_texto(reais_curto(v), 10, rgba(CORES["texto2"]))
                Rectangle(texture=tex, pos=(self.x + px - tex.width / 2, self.y + py - dp(20)), size=tex.size)
            # ---- 5) SETA no fim da trilha: T · R · S (gira na direção da curva)
            if len(curva_futuro) > 1:
                a, b = curva_futuro[-2], curva_futuro[-1]
                ang = math.atan2(b[1] - a[1], b[0] - a[0]) - math.pi / 2
                seta = [(0, 10), (-7, -5), (0, -1), (7, -5)]
                M = tf.compor(tf.translacao2d(self.x + b[0], self.y + b[1]), tf.rotacao2d(ang), tf.escala2d(dp(1.3)))
                Color(*rgba(CORES["dourado"]))
                p = tf.aplicar2d(M, seta)
                malha_poligono([p[0], p[1], p[2]])
                malha_poligono([p[0], p[2], p[3]])
        self._desenhar_avatar()

    # ---- 6) AVATAR: segue a curva com T (translação) e "respira" com S (escala)
    def _pulsar(self, dt):
        self._t += dt
        self._desenhar_avatar()

    def _desenhar_avatar(self, *_):
        g = self._grupo_avatar
        g.clear()
        c = self._curva_hist
        if c is None or len(c) < 2:
            return
        pos = c[int(round(self.avanco * (len(c) - 1)))]
        cx, cy = self.x + pos[0], self.y + pos[1]
        pulso = 1 + 0.18 * math.sin(self._t * 3)
        halo = tf.aplicar2d(tf.compor(tf.translacao2d(cx, cy), tf.escala2d(dp(9) * pulso)), circulo(0, 0, 1, 24))
        g.add(Color(*rgba(CORES["dourado"], 0.35)))
        g.add(malha_poligono(halo))
        # pessoa: cabeça (círculo) + corpo (polígono), em coordenadas locais
        M = tf.compor(tf.translacao2d(cx, cy + dp(4)), tf.escala2d(dp(1.25)))
        corpo = tf.aplicar2d(M, [(-6, 0), (6, 0), (5.5, 8), (3, 10), (-3, 10), (-5.5, 8)])
        cabeca = tf.aplicar2d(M, circulo(0, 14.5, 4.2, 16))
        g.add(Color(*rgba(CORES["grafite"])))
        g.add(malha_poligono(corpo))
        g.add(Color(*rgba(CORES["amarelo"])))
        g.add(malha_poligono(cabeca))


# =====================================================================
# Moeda 3D girando (cartão de pontos)
# =====================================================================
class MoedaGiratoria(Widget):
    cor = StringProperty(CORES["dourado"])

    def __init__(self, **kw):
        super().__init__(**kw)
        self.angulo = 0.0
        with self.canvas:
            self._cor_tras = Color(1, 1, 1, 1)
            self._tras = Mesh(mode="triangle_fan")
            self._cor_frente = Color(1, 1, 1, 1)
            self._frente = Mesh(mode="triangle_fan")
            self._cor_estrela = Color(1, 1, 1, 1)
            self._estrela1 = Mesh(mode="triangle_fan")
            self._estrela2 = Mesh(mode="triangle_fan")
        self._evento = Clock.schedule_interval(self._girar, 1 / 30)

    def _girar(self, dt):
        self.angulo += dt * 2.0
        r = min(self.width, self.height) / 2 * 0.92
        if r <= 1:
            return
        esp = r * 0.18
        # OBJETO 3D: dois discos (frente e verso) com espessura
        ang = np.linspace(0, 2 * math.pi, 28, endpoint=False)
        disco = np.stack([np.cos(ang) * r, np.sin(ang) * r, np.zeros_like(ang)], axis=1)
        frente, verso = disco + [0, 0, esp / 2], disco - [0, 0, esp / 2]
        # TRANSFORMAÇÃO 3D: inclina um pouco em X e gira em Y
        M = tf.compor(tf.rotacao_x(0.25), tf.rotacao_y(self.angulo))
        f3, v3 = tf.aplicar3d(M, frente), tf.aplicar3d(M, verso)
        # PROJEÇÃO em perspectiva + posição na tela
        centro = np.array([self.center_x, self.center_y])
        f2, v2 = tf.projetar(f3, r * 8) + centro, tf.projetar(v3, r * 8) + centro
        # ALGORITMO DO PINTOR: desenha primeiro o disco mais distante (menor z)
        perto, longe = (f2, v2) if f3[:, 2].mean() > v3[:, 2].mean() else (v2, f2)
        # SHADING: quanto mais o disco "olha" para a câmera, mais claro
        nz = abs(tf.aplicar3d(M, [(0, 0, 1)])[0][2] - tf.aplicar3d(M, [(0, 0, 0)])[0][2])
        base = np.array(rgba(self.cor)[:3])
        self._cor_tras.rgba = (*(base * 0.55), 1)
        self._cor_frente.rgba = (*np.clip(base * (0.55 + 0.5 * nz), 0, 1), 1)
        self._cor_estrela.rgba = (*np.clip(base * (0.8 + 0.4 * nz) + 0.15, 0, 1), 1)
        atualizar_malha(self._tras, longe)
        atualizar_malha(self._frente, perto)
        # estrela em relevo na face da frente
        z_face = esp / 2 + 0.5 if perto is f2 else -esp / 2 - 0.5
        estrela = []
        for i in range(10):
            a = math.pi / 2 + i * math.pi / 5
            rr = r * (0.55 if i % 2 == 0 else 0.24)
            estrela.append((math.cos(a) * rr, math.sin(a) * rr, z_face))
        e2 = tf.projetar(tf.aplicar3d(M, estrela), r * 8) + centro
        # estrela = 2 polígonos convexos (pentágono interno + pontas como leques)
        atualizar_malha(self._estrela1, [e2[i] for i in range(1, 10, 2)])
        pontas = []
        for i in range(0, 10, 2):
            pontas += [e2[(i - 1) % 10], e2[i], e2[(i + 1) % 10]]
        vertices = []
        for x, y in pontas:
            vertices += [float(x), float(y), 0.0, 0.0]
        self._estrela2.vertices = vertices
        self._estrela2.indices = list(range(len(pontas)))
        self._estrela2.mode = "triangles"

    def parar(self):
        self._evento.cancel()


# =====================================================================
# Anel do crédito progressivo (rasterizado com antialiasing)
# =====================================================================
class AnelCredito(Widget):
    fracao = NumericProperty(0)
    antialias = BooleanProperty(True)
    abertura = NumericProperty(360)
    inicio = NumericProperty(90)
    cores = ListProperty(["#F2C230", "#F5B700", "#D99A00"])
    espessura = NumericProperty(dp(7))

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas:
            Color(1, 1, 1, 1)
            self._ret = Rectangle()
        self._agendar = Clock.create_trigger(self._redesenhar, 0)
        self.bind(size=self._agendar, pos=self._agendar, fracao=self._agendar, antialias=self._agendar)

    def _redesenhar(self, *_):
        lado = int(min(self.width, self.height))
        if lado < 8:
            return
        img = raster.rasterizar_anel(lado, self.espessura, self.fracao, CORES["cinza_claro"], self.cores,
                                     self.antialias, self.inicio, self.abertura)
        self._ret.texture = raster.para_textura(img)
        self._ret.size = (lado, lado)
        self._ret.pos = (self.center_x - lado / 2, self.center_y - lado / 2)


# =====================================================================
# Medalha com iluminação de Phong
# =====================================================================
class Medalha(Widget):
    cor = StringProperty(CORES["dourado"])
    ativa = BooleanProperty(True)
    luz_x = NumericProperty(-0.5)

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas:
            self._c = Color(1, 1, 1, 1)
            self._ret = Rectangle()
        self._agendar = Clock.create_trigger(self._redesenhar, 0)
        self.bind(size=self._agendar, pos=self._agendar, cor=self._agendar, ativa=self._agendar, luz_x=self._agendar)

    def _redesenhar(self, *_):
        lado = int(min(self.width, self.height))
        if lado < 8:
            return
        cor = self.cor if self.ativa else "#D5D9DF"
        img = raster.esfera_iluminada(lado, cor, luz=(self.luz_x, 0.6, 0.7), brilho_especular=0.8 if self.ativa else 0.2)
        self._ret.texture = raster.para_textura(img)
        self._ret.size = (lado, lado)
        self._ret.pos = (self.center_x - lado / 2, self.center_y - lado / 2)
