"""
LABORATÓRIO DE COMPUTAÇÃO GRÁFICA
================================
Tela feita para a APRESENTAÇÃO: mostra, de forma interativa, os
conteúdos da disciplina que estão funcionando "por baixo" do app.

 1. Rasterização e antialiasing  → grade de pixels ampliada (Bresenham × superamostragem)
 2. Recorte (Cohen–Sutherland)   → arraste as pontas da linha
 3. Transformações 3D e projeção → cartão em modo aramado + matriz ao vivo
 4. Iluminação (Phong)           → mova a luz e veja o brilho mudar
"""
import math

import numpy as np
from kivy.clock import Clock
from kivy.graphics import Color, Line, Rectangle
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import NumericProperty, OptionProperty, StringProperty
from kivy.uix.widget import Widget

from cg import raster, recorte, transformacoes as tf
from tema import CORES, rgba
from telas.componentes import TelaVertis

Builder.load_string("""
#:import rgba tema.rgba
#:import CORES tema.CORES

<Secao@Painel>:
    orientation: 'vertical'
    size_hint_y: None
    height: self.minimum_height

<TelaLab>:
    BoxLayout:
        orientation: 'vertical'
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            padding: dp(16), dp(8), dp(16), 0
            TextoTitulo:
                text: 'Laboratório de CG'
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: dp(14), dp(6), dp(14), dp(20)
                spacing: dp(14)

                Secao:
                    Texto:
                        text: '[b]1. Rasterização e antialiasing[/b]'
                    TextoPequeno:
                        text: 'Cada quadrado é um PIXEL ampliado. A linha branca é a linha "matemática".\\nSerrilhado (Bresenham): pixel 100% aceso ou apagado. Suave (superamostragem 4x4): cada pixel recebe a FRAÇÃO coberta pela linha.'
                    GradePixels:
                        id: grade
                        size_hint_y: None
                        height: dp(200)
                        angulo: slider_ang.value
                    Slider:
                        id: slider_ang
                        min: 5
                        max: 85
                        value: 28
                        size_hint_y: None
                        height: dp(30)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(40)
                        spacing: dp(10)
                        BotaoVertis:
                            text: 'Serrilhado'
                            height: dp(40)
                            cor: rgba(CORES['roxo']) if grade.modo == 'serrilhado' else rgba('#3B2A66')
                            on_release: grade.modo = 'serrilhado'
                        BotaoVertis:
                            text: 'Suave (antialiasing)'
                            height: dp(40)
                            cor: rgba(CORES['roxo']) if grade.modo == 'suave' else rgba('#3B2A66')
                            on_release: grade.modo = 'suave'

                Secao:
                    Texto:
                        text: '[b]2. Recorte de Cohen–Sutherland[/b]'
                    TextoPequeno:
                        text: 'Arraste as pontas da linha. Só a parte dentro da JANELA (retângulo) é desenhada. Cada ponta tem um código de 4 bits: [acima][abaixo][direita][esquerda].'
                    DemoRecorte:
                        id: rec
                        size_hint_y: None
                        height: dp(230)
                    TextoPequeno:
                        text: rec.info
                        color: rgba(CORES['dourado_claro'])

                Secao:
                    Texto:
                        text: '[b]3. Objeto 3D, transformações e projeção[/b]'
                    TextoPequeno:
                        text: 'O cartão é uma malha de faixas. Gire com o dedo: a matriz M = Rx·Ry muda ao vivo. A perspectiva divide x e y por w = 1 − z/d (o que está longe fica menor). Faces de costas são descartadas (back-face culling).'
                    Cartao3D:
                        id: c3d
                        size_hint_y: None
                        height: dp(190)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(40)
                        spacing: dp(10)
                        BotaoVertis:
                            text: 'Aramado: ' + ('SIM' if c3d.aramado else 'NÃO')
                            height: dp(40)
                            on_release: c3d.aramado = not c3d.aramado
                        BotaoVertis:
                            text: 'Iluminação: ' + ('SIM' if c3d.iluminacao else 'NÃO')
                            height: dp(40)
                            on_release: c3d.iluminacao = not c3d.iluminacao
                    Label:
                        text: root.matriz
                        font_name: 'RobotoMono-Regular'
                        font_size: sp(11)
                        color: rgba(CORES['dourado_claro'])
                        size_hint_y: None
                        height: dp(76)

                Secao:
                    Texto:
                        text: '[b]4. Iluminação de Phong (por pixel)[/b]'
                    TextoPequeno:
                        text: 'intensidade = ambiente + difusa·(N·L) + especular·(R·V)^n\\nN = normal da esfera, L = direção da luz, V = olho. Mova a luz:'
                    Medalha:
                        size_hint_y: None
                        height: dp(150)
                        cor: CORES['dourado']
                        luz_x: slider_luz.value
                    Slider:
                        id: slider_luz
                        min: -1
                        max: 1
                        value: -0.5
                        size_hint_y: None
                        height: dp(30)
        BarraNavegacao:
            atual: 'lab'
""")


class GradePixels(Widget):
    """Grade 32×18 de pixels ampliados para ver a rasterização de perto."""
    angulo = NumericProperty(28)
    modo = OptionProperty("suave", options=["serrilhado", "suave"])
    COLS, LINHAS = 32, 18

    def __init__(self, **kw):
        super().__init__(**kw)
        self._agendar = Clock.create_trigger(self._redesenhar, 0)
        self.bind(size=self._agendar, pos=self._agendar, angulo=self._agendar, modo=self._agendar)

    def _redesenhar(self, *_):
        C, L = self.COLS, self.LINHAS
        x0, y0 = 1.5, 1.5
        comp = 40
        x1 = x0 + comp * math.cos(math.radians(self.angulo))
        y1 = y0 + comp * math.sin(math.radians(self.angulo))
        img = np.zeros((L, C, 4), np.uint8)
        img[..., :3] = (34, 22, 74)
        img[..., 3] = 255
        cor = np.array([245, 184, 61])
        if self.modo == "serrilhado":
            for px, py in raster.bresenham(int(x0), int(y0), int(round(x1)), int(round(y1))):
                if 0 <= px < C and 0 <= py < L:
                    img[py, px, :3] = cor
        else:
            cob = raster.cobertura_linha(C, L, x0 + 0.5, y0 + 0.5, x1 + 0.5, y1 + 0.5, espessura=1.0, amostras=4)
            img[..., :3] = (img[..., :3] * (1 - cob[..., None]) + cor * cob[..., None]).astype(np.uint8)
        lado = min(self.width / C, self.height / L)
        larg, alt = lado * C, lado * L
        ox, oy = self.center_x - larg / 2, self.center_y - alt / 2
        self.canvas.clear()
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(texture=raster.para_textura(img, filtro_suave=False), pos=(ox, oy), size=(larg, alt))
            Color(1, 1, 1, 0.08)                       # linhas da grade
            for i in range(C + 1):
                Line(points=[ox + i * lado, oy, ox + i * lado, oy + alt], width=1)
            for j in range(L + 1):
                Line(points=[ox, oy + j * lado, ox + larg, oy + j * lado], width=1)
            Color(1, 1, 1, 0.9)                        # a linha "ideal", RECORTADA na grade
            visivel = recorte.cohen_sutherland(ox + (x0 + 0.5) * lado, oy + (y0 + 0.5) * lado,
                                               ox + (x1 + 0.5) * lado, oy + (y1 + 0.5) * lado,
                                               ox, oy, ox + larg, oy + alt)
            if visivel:
                Line(points=list(visivel), width=1)


class DemoRecorte(Widget):
    info = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.p = [[0.05, 0.85], [0.92, 0.12]]   # pontas em coordenadas relativas (0 a 1)
        self._pegou = None
        self.bind(size=self._redesenhar, pos=self._redesenhar)

    def _janela(self):
        return (self.x + self.width * 0.22, self.y + self.height * 0.22,
                self.x + self.width * 0.78, self.y + self.height * 0.78)

    def _abs(self, i):
        return self.x + self.p[i][0] * self.width, self.y + self.p[i][1] * self.height

    def on_touch_down(self, t):
        if not self.collide_point(*t.pos):
            return super().on_touch_down(t)
        dist = [math.dist(t.pos, self._abs(i)) for i in range(2)]
        self._pegou = int(np.argmin(dist))
        t.grab(self)
        self.on_touch_move(t)
        return True

    def on_touch_move(self, t):
        if t.grab_current is self:
            self.p[self._pegou] = [min(1, max(0, (t.x - self.x) / self.width)),
                                   min(1, max(0, (t.y - self.y) / self.height))]
            self._redesenhar()
            return True
        return super().on_touch_move(t)

    def on_touch_up(self, t):
        if t.grab_current is self:
            t.ungrab(self)
            return True
        return super().on_touch_up(t)

    def _redesenhar(self, *_):
        xmin, ymin, xmax, ymax = self._janela()
        (ax, ay), (bx, by) = self._abs(0), self._abs(1)
        r = recorte.cohen_sutherland(ax, ay, bx, by, xmin, ymin, xmax, ymax)
        c0 = recorte.codigo_regiao(ax, ay, xmin, ymin, xmax, ymax)
        c1 = recorte.codigo_regiao(bx, by, xmin, ymin, xmax, ymax)
        if r is None:
            resultado = "linha DESCARTADA (fora da janela)" if c0 & c1 else "linha fora da janela"
        elif not (c0 | c1):
            resultado = "linha ACEITA inteira"
        else:
            resultado = "linha RECORTADA na borda"
        self.info = f"P0 = {c0:04b}   P1 = {c1:04b}   »  {resultado}"
        self.canvas.clear()
        with self.canvas:
            Color(*rgba("#1A0F3D"))
            Rectangle(pos=self.pos, size=self.size)
            Color(*rgba(CORES["lilas"], 0.25))           # as 9 regiões
            for x in (xmin, xmax):
                Line(points=[x, self.y, x, self.top], width=1, dash_length=4, dash_offset=4)
            for y in (ymin, ymax):
                Line(points=[self.x, y, self.right, y], width=1, dash_length=4, dash_offset=4)
            Color(*rgba(CORES["lilas"]))                 # a janela de recorte
            Line(rectangle=(xmin, ymin, xmax - xmin, ymax - ymin), width=1.6)
            Color(1, 1, 1, 0.25)                         # linha original (invisível na prática)
            Line(points=[ax, ay, bx, by], width=1, dash_length=6, dash_offset=4)
            if r:
                Color(*rgba(CORES["dourado"]))           # parte visível
                Line(points=list(r), width=dp(2.2))
            for (px, py) in ((ax, ay), (bx, by)):
                Color(*rgba(CORES["rosa"]))
                Line(circle=(px, py, dp(7)), width=dp(1.5))


class TelaLab(TelaVertis):
    matriz = StringProperty("")

    def on_enter(self, *_):
        self._ev = Clock.schedule_interval(self._mostrar_matriz, 0.2)
        c = self.ids.c3d
        if not c.dados:
            c.dados = {"nome": "LABORATORIO CG", "final": "2026", "validade": "11/26", "nivel": "Lab", "limite": "-"}

    def on_leave(self, *_):
        self._ev.cancel()

    def _mostrar_matriz(self, *_):
        self.matriz = "M = Rx · Ry =\n" + tf.formatar_matriz(self.ids.c3d.matriz())
