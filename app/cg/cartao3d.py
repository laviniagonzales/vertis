"""
CARTÃO DE CRÉDITO EM 3D
=======================
Conteúdo da disciplina reunido num só objeto:

 1. DEFINIÇÃO DO OBJETO 3D: o cartão é uma "caixa" fina (frente, verso e
    4 laterais). A frente e o verso são divididos em FAIXAS (malha).
 2. TRANSFORMAÇÕES 3D: matriz M = Rx(ângulo_x) · Ry(ângulo_y)
    (o usuário gira o cartão arrastando o dedo).
 3. PROJEÇÃO EM PERSPECTIVA: x' = x / w, y' = y / w, com w = 1 − z/d.
 4. VISIBILIDADE:
      • back-face culling: se a normal da face aponta para longe da
        câmera, a face não é desenhada (vemos o VERSO quando ele vira);
      • algoritmo do pintor: desenha do mais longe para o mais perto.
 5. ILUMINAÇÃO / SHADING (Phong por faixa):
      intensidade = ambiente + difusa·(N·L)  e  brilho especular (R·V)^n
 6. TEXTURAS E MAPEAMENTO: a arte do cartão é desenhada numa textura
    (Fbo = "tela fora da tela") e cada faixa recebe as coordenadas (u, v)
    da parte da textura que lhe cabe.
"""
import math

import numpy as np
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Fbo, Line, Mesh, Rectangle, RoundedRectangle, ClearColor, ClearBuffers
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, DictProperty, NumericProperty
from kivy.uix.widget import Widget
from kivy.animation import Animation

from cg import raster, transformacoes as tf
from tema import CORES, rgba

LARG, ALT, ESP = 3.4, 2.14, 0.07     # proporção de um cartão real (85,6 × 54 mm)
FAIXAS = 14                          # quantas faixas na malha da frente/verso
DIST_CAMERA = 9.0
LUZ = np.array([-3.0, 4.0, 7.0])


def _texto(t, tam, negrito=False, cor=(1, 1, 1, 1), fonte=None):
    kw = {"font_size": tam, "bold": negrito, "color": cor}
    if fonte:
        kw["font_name"] = fonte
    r = CoreLabel(text=t, **kw)
    r.refresh()
    return r.texture


class Cartao3D(Widget):
    angulo_x = NumericProperty(-0.18)
    angulo_y = NumericProperty(0.35)
    aramado = BooleanProperty(False)        # mostra só as arestas da malha (wireframe)
    iluminacao = BooleanProperty(True)
    dados = DictProperty({})                # nome, final, validade, nível, limite...

    def __init__(self, **kw):
        super().__init__(**kw)
        self._tex_frente = self._tex_verso = None
        self._arrastando = False
        self._balanco = 0.0
        self._ultima_matriz = np.identity(4)
        self.bind(dados=self._refazer_texturas)
        Clock.schedule_interval(self._quadro, 1 / 30)

    # ---------------------------------------------------------- texturas (Fbo)
    def _refazer_texturas(self, *_):
        self._tex_frente = self._tex_verso = None

    def _criar_texturas(self):
        W, H = 640, 404
        d = self.dados
        fundo = raster.para_textura(raster.gradiente_diagonal(64, 40, ["#1C1F24", "#2E333B", "#3D434C"]))
        frente = Fbo(size=(W, H))
        with frente:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=(0, 0), size=(W, H), radius=[34], texture=fundo)
            # brilho diagonal decorativo
            Color(1, 1, 1, 0.07)
            RoundedRectangle(pos=(W * 0.45, 0), size=(W * 0.55, H), radius=[34])
            # logo: barras crescentes (o "crescimento vertical" da marca)
            Color(*rgba(CORES["dourado"]))
            for i, h in enumerate((18, 28, 40)):
                RoundedRectangle(pos=(40 + i * 15, H - 78), size=(10, h), radius=[3])
            t = _texto("VÉRTIS", 42, True)
            Color(1, 1, 1, 1)
            Rectangle(texture=t, pos=(95, H - 82), size=t.size)
            t = _texto(d.get("nivel", "Semente").upper(), 20, True, rgba("#FFD24D"))
            Rectangle(texture=t, pos=(W - t.width - 40, H - 72), size=t.size)
            # chip
            Color(*rgba("#E9C46A"))
            RoundedRectangle(pos=(48, H / 2 - 30), size=(78, 58), radius=[10])
            Color(*rgba("#B8892B"))
            for k in range(3):
                Line(points=[48, H / 2 - 12 + k * 14, 126, H / 2 - 12 + k * 14], width=1.4)
            Line(points=[87, H / 2 - 30, 87, H / 2 + 28], width=1.4)
            # símbolo de aproximação (arcos)
            Color(1, 1, 1, 0.8)
            for k in range(3):
                Line(circle=(150, H / 2, 12 + k * 9, 50, 130), width=2)
            t = _texto(f"••••  ••••  ••••  {d.get('final', '0000')}", 34, True)
            Color(1, 1, 1, 1)
            Rectangle(texture=t, pos=(46, 112), size=t.size)
            t = _texto(d.get("nome", "CLIENTE VÉRTIS"), 24, True)
            Rectangle(texture=t, pos=(46, 50), size=t.size)
            t = _texto(f"VAL {d.get('validade', '00/00')}", 20, False, (1, 1, 1, 0.85))
            Rectangle(texture=t, pos=(W / 2 + 10, 54), size=t.size)
            t = _texto(d.get("bandeira", "Mastercard"), 22, True, (1, 1, 1, 0.9))
            Rectangle(texture=t, pos=(W - t.width - 40, 52), size=t.size)
        frente.draw()

        verso = Fbo(size=(W, H))
        with verso:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=(0, 0), size=(W, H), radius=[34], texture=fundo)
            Color(0.06, 0.04, 0.12, 1)
            Rectangle(pos=(0, H - 110), size=(W, 64))            # tarja magnética
            Color(0.95, 0.95, 0.97, 1)
            Rectangle(pos=(40, H - 200), size=(400, 52))          # tarja de assinatura
            t = _texto("CVV •••", 22, True, (0.1, 0.1, 0.2, 1))
            Color(1, 1, 1, 1)
            Rectangle(texture=t, pos=(460, H - 190), size=t.size)
            t = _texto(f"Limite atual: {d.get('limite', '')}", 26, True, rgba("#FFD24D"))
            Rectangle(texture=t, pos=(40, 110), size=t.size)
            t = _texto("Crédito progressivo: pague em dia e seu limite cresce.", 18, False, (1, 1, 1, 0.85))
            Rectangle(texture=t, pos=(40, 70), size=t.size)
            t = _texto("Vértis • Crescimento vertical", 18, False, (1, 1, 1, 0.6))
            Rectangle(texture=t, pos=(40, 30), size=t.size)
        verso.draw()

        # máscara branca com o mesmo formato (cantos arredondados) — usada no reflexo especular
        mascara = Fbo(size=(W, H))
        with mascara:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()
            Color(1, 1, 1, 1)
            RoundedRectangle(pos=(0, 0), size=(W, H), radius=[34])
        mascara.draw()
        self._tex_frente, self._tex_verso, self._tex_mascara = frente.texture, verso.texture, mascara.texture

    # ---------------------------------------------------------- interação
    def on_touch_down(self, toque):
        if self.collide_point(*toque.pos):
            self._arrastando = True
            toque.grab(self)
            return True
        return super().on_touch_down(toque)

    def on_touch_move(self, toque):
        if toque.grab_current is self:
            self.angulo_y += toque.dx * 0.012
            self.angulo_x = max(-1.2, min(1.2, self.angulo_x - toque.dy * 0.012))
            return True
        return super().on_touch_move(toque)

    def on_touch_up(self, toque):
        if toque.grab_current is self:
            toque.ungrab(self)
            self._arrastando = False
            return True
        return super().on_touch_up(toque)

    def virar(self):
        """Gira 180° em Y com animação — mostra o verso (ou a frente)."""
        alvo = round(self.angulo_y / math.pi) * math.pi + math.pi
        Animation(angulo_y=alvo, d=0.8, t="in_out_cubic").start(self)

    # ---------------------------------------------------------- desenho
    def matriz(self):
        return tf.compor(tf.rotacao_x(self.angulo_x), tf.rotacao_y(self.angulo_y + self._balanco))

    def _quadro(self, dt):
        if not self._arrastando:
            self._balanco = 0.12 * math.sin(Clock.get_boottime() * 0.9)   # leve balanço "vivo"
        if self._tex_frente is None:
            self._criar_texturas()
        self._desenhar()

    def _sombrear(self, ponto, normal):
        """Modelo de iluminação de PHONG para um ponto da superfície."""
        if not self.iluminacao:
            return 1.0, 0.0
        camera = np.array([0, 0, DIST_CAMERA])
        L = tf.normalizar(LUZ - ponto)
        V = tf.normalizar(camera - ponto)
        difusa = max(0.0, float(normal @ L))
        R = 2 * float(normal @ L) * normal - L                   # vetor de reflexão
        especular = max(0.0, float(R @ V)) ** 18 * 0.55
        return min(1.0, 0.38 + 0.72 * difusa), especular

    def _desenhar(self):
        M = self.matriz()
        self._ultima_matriz = M
        escala = min(self.width / (LARG * 1.18), self.height / (ALT * 1.45))
        centro = np.array([self.center_x, self.center_y])
        camera = np.array([0, 0, DIST_CAMERA])

        def tela(pontos3d):
            return tf.projetar(pontos3d, DIST_CAMERA) * escala + centro

        rot = M[:3, :3]                         # parte de rotação (para girar as normais)
        faces = []                              # (profundidade, tipo, dados)

        # --- frente (z = +ESP/2) e verso (z = −ESP/2), divididos em faixas
        xs = np.linspace(-LARG / 2, LARG / 2, FAIXAS + 1)
        for lado, z, normal_local in (("frente", ESP / 2, (0, 0, 1)), ("verso", -ESP / 2, (0, 0, -1))):
            normal = rot @ np.array(normal_local, float)
            centro_face = tf.aplicar3d(M, [(0, 0, z)])[0]
            # BACK-FACE CULLING: só desenha se a face está virada para a câmera
            if normal @ (camera - centro_face) <= 0:
                continue
            for i in range(FAIXAS):
                quad = [(xs[i], -ALT / 2, z), (xs[i + 1], -ALT / 2, z), (xs[i + 1], ALT / 2, z), (xs[i], ALT / 2, z)]
                q3 = tf.aplicar3d(M, quad)
                u0, u1 = (i / FAIXAS, (i + 1) / FAIXAS)
                if lado == "verso":              # visto por trás, a textura é espelhada
                    u0, u1 = 1 - u0, 1 - u1
                faces.append((q3[:, 2].mean(), lado, (tela(q3), (u0, u1), self._sombrear(q3.mean(axis=0), normal))))

        # --- laterais (bordas finas), encurtadas nas pontas por causa dos cantos arredondados
        r = 0.16
        laterais = [
            ([(-LARG / 2 + r, ALT / 2, -ESP / 2), (LARG / 2 - r, ALT / 2, -ESP / 2), (LARG / 2 - r, ALT / 2, ESP / 2), (-LARG / 2 + r, ALT / 2, ESP / 2)], (0, 1, 0)),
            ([(-LARG / 2 + r, -ALT / 2, ESP / 2), (LARG / 2 - r, -ALT / 2, ESP / 2), (LARG / 2 - r, -ALT / 2, -ESP / 2), (-LARG / 2 + r, -ALT / 2, -ESP / 2)], (0, -1, 0)),
            ([(LARG / 2, -ALT / 2 + r, ESP / 2), (LARG / 2, ALT / 2 - r, ESP / 2), (LARG / 2, ALT / 2 - r, -ESP / 2), (LARG / 2, -ALT / 2 + r, -ESP / 2)], (1, 0, 0)),
            ([(-LARG / 2, -ALT / 2 + r, -ESP / 2), (-LARG / 2, ALT / 2 - r, -ESP / 2), (-LARG / 2, ALT / 2 - r, ESP / 2), (-LARG / 2, -ALT / 2 + r, ESP / 2)], (-1, 0, 0)),
        ]
        for quad, n in laterais:
            q3 = tf.aplicar3d(M, quad)
            normal = rot @ np.array(n, float)
            if normal @ (camera - q3.mean(axis=0)) > 0:
                faces.append((q3[:, 2].mean() - 1, "lateral", (tela(q3), None, self._sombrear(q3.mean(axis=0), normal))))

        # ALGORITMO DO PINTOR: do mais distante (z menor) para o mais próximo
        faces.sort(key=lambda f: f[0])

        self.canvas.clear()
        with self.canvas:
            # sombra no "chão"
            Color(0, 0, 0, 0.28)
            from kivy.graphics import Ellipse
            Ellipse(pos=(self.center_x - LARG * escala * 0.45, self.y + dp(2)), size=(LARG * escala * 0.9, dp(14)))
            for _, tipo, (p2, uv, (luz, brilho)) in faces:
                if self.aramado:
                    Color(*rgba(CORES["amarelo"]))
                    Line(points=[*p2[0], *p2[1], *p2[2], *p2[3], *p2[0], *p2[2]], width=1)
                    continue
                if tipo == "lateral":
                    Color(0.25 * luz + 0.1, 0.12 * luz + 0.05, 0.45 * luz + 0.1, 1)
                    Mesh(vertices=[c for p in p2 for c in (*p, 0, 0)], indices=[0, 1, 2, 2, 3, 0], mode="triangles")
                    continue
                tex = self._tex_frente if tipo == "frente" else self._tex_verso
                u0, u1 = uv
                # MAPEAMENTO DE TEXTURA: cada vértice recebe (x, y, u, v)
                vertices = [*p2[0], u0, 0, *p2[1], u1, 0, *p2[2], u1, 1, *p2[3], u0, 1]
                Color(luz, luz, luz, 1)
                Mesh(vertices=vertices, indices=[0, 1, 2, 2, 3, 0], mode="triangles", texture=tex)
                if brilho > 0.01:     # reflexo especular: luz branca por cima da faixa
                    Color(1, 1, 1, min(0.6, brilho))
                    Mesh(vertices=vertices, indices=[0, 1, 2, 2, 3, 0], mode="triangles",
                         texture=self._tex_mascara)
