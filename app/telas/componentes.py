"""
COMPONENTES REUTILIZADOS POR TODAS AS TELAS
==========================================
O visual é descrito em "KV" (a linguagem de layout do Kivy, parecida com CSS)
e o comportamento em Python.
"""
from kivy.animation import Animation
from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, PopMatrix, PushMatrix, RoundedRectangle, Scale
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ColorProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from cg.widgets import Medalha
from tema import CORES, rgba

Builder.load_string("""
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp
#:import rgba tema.rgba
#:import CORES tema.CORES

<TelaVertis>:
    FundoGradiente:
        pos: 0, 0
        size: root.size

<Painel>:
    padding: dp(12)
    spacing: dp(6)
    canvas.before:
        Color:
            rgba: self.cor_fundo
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(16)]
        Color:
            rgba: self.cor_borda
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(16))
            width: 1

<Texto@Label>:
    color: rgba(CORES['texto'])
    font_size: sp(14)
    halign: 'left'
    valign: 'middle'
    text_size: self.width, None
    size_hint_y: None
    height: self.texture_size[1]
    markup: True

<TextoPequeno@Texto>:
    color: rgba(CORES['texto2'])
    font_size: sp(12)

<TextoTitulo@Texto>:
    font_size: sp(20)
    bold: True

<BotaoVertis>:
    color: self.cor_texto
    font_size: sp(15)
    bold: True
    size_hint_y: None
    height: dp(46)
    canvas.before:
        Color:
            rgba: (self.cor[0] * 0.75, self.cor[1] * 0.75, self.cor[2] * 0.75, 1) if self.state == 'down' else self.cor
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]

<BotaoContorno@ButtonBehavior+Label>:
    color: rgba(CORES['lilas'])
    font_size: sp(14)
    bold: True
    size_hint_y: None
    height: dp(40)
    canvas.before:
        Color:
            rgba: rgba(CORES['lilas'], 0.25 if self.state == 'down' else 0.0)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]
        Color:
            rgba: rgba(CORES['lilas'], 0.8)
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(12))
            width: 1.2

<Campo@TextInput>:
    multiline: False
    write_tab: False
    size_hint_y: None
    height: dp(44)
    padding: dp(12), dp(12)
    background_normal: ''
    background_active: ''
    background_color: rgba('#1C1240')
    foreground_color: 1, 1, 1, 1
    hint_text_color: rgba(CORES['texto2'], 0.7)
    cursor_color: rgba(CORES['dourado'])
    font_size: sp(15)

<BarraProgresso>:
    size_hint_y: None
    height: dp(8)
    canvas:
        Color:
            rgba: rgba('#3B2A66')
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.height / 2]
        Color:
            rgba: self.cor
        RoundedRectangle:
            pos: self.pos
            size: max(self.height, self.width * min(1, max(0, self.valor))), self.height
            radius: [self.height / 2]

<BotaoNav>:
    color: rgba(CORES['dourado']) if self.ativo else rgba(CORES['texto2'])
    font_size: sp(11)
    bold: self.ativo
    canvas.before:
        Color:
            rgba: rgba(CORES['dourado'], 1 if self.ativo else 0)
        RoundedRectangle:
            pos: self.center_x - dp(14), self.top - dp(4)
            size: dp(28), dp(3)
            radius: [dp(2)]

<BarraNavegacao>:
    size_hint_y: None
    height: dp(54)
    canvas.before:
        Color:
            rgba: rgba('#140B2E', 0.96)
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: rgba('#5B45A8', 0.5)
        Line:
            points: self.x, self.top, self.right, self.top
""")


class TelaVertis(Screen):
    """Tela base: já vem com o fundo em degradê."""


# Classes com propriedades próprias são declaradas em Python (com valor padrão);
# o visual delas está no KV acima.
class Painel(BoxLayout):
    cor_fundo = ColorProperty(rgba("#22164A", 0.88))
    cor_borda = ColorProperty(rgba("#5B45A8", 0.55))


class BotaoVertis(ButtonBehavior, Label):
    cor = ColorProperty(rgba(CORES["roxo"]))
    cor_texto = ColorProperty([1, 1, 1, 1])


class BarraProgresso(Widget):
    valor = NumericProperty(0)
    cor = ColorProperty(rgba(CORES["dourado"]))


class BotaoNav(ButtonBehavior, Label):
    ativo = BooleanProperty(False)
    destino = StringProperty("")


class BarraNavegacao(BoxLayout):
    ITENS = [("inicio", "Início"), ("conta", "Conta"), ("cartao", "Cartão"),
             ("conquistas", "Conquistas"), ("lab", "Lab CG")]
    atual = StringProperty("inicio")

    def __init__(self, **kw):
        super().__init__(**kw)
        for destino, nome in self.ITENS:
            b = BotaoNav(text=nome, destino=destino, ativo=(destino == self.atual))
            b.bind(on_release=lambda btn: App.get_running_app().ir(btn.destino))
            self.add_widget(b)
        self.bind(atual=self._marcar)

    def _marcar(self, *_):
        for b in self.children:
            b.ativo = (b.destino == self.atual)


# ---------------------------------------------------------------- aviso rápido (toast)
def aviso(texto, erro=False):
    rot = Label(text=texto, font_size=sp(13), color=(1, 1, 1, 1), size_hint=(None, None),
                halign="center", valign="middle")
    rot.text_size = (Window.width * 0.82, None)
    rot.texture_update()
    rot.size = (Window.width * 0.86, rot.texture_size[1] + dp(22))
    rot.pos = ((Window.width - rot.width) / 2, dp(70))
    with rot.canvas.before:
        Color(*rgba(CORES["vermelho"] if erro else "#2E1F63", 0.97))
        RoundedRectangle(pos=rot.pos, size=rot.size, radius=[dp(12)])
    Window.add_widget(rot)
    anim = Animation(d=2.6 if not erro else 3.6) + Animation(opacity=0, d=0.4)
    anim.bind(on_complete=lambda *_: Window.remove_widget(rot))
    anim.start(rot)


# ---------------------------------------------------------------- celebração
class MedalhaAnimada(Widget):
    """Medalha que "explode" na tela: TRANSFORMAÇÃO DE ESCALA (S) animada de 0 → 1."""
    escala = NumericProperty(0.01)
    cor = StringProperty(CORES["dourado"])

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            PushMatrix()
            self._s = Scale(1, 1, 1)
        with self.canvas.after:
            PopMatrix()
        self.medalha = Medalha(cor=self.cor)
        self.add_widget(self.medalha)
        self.bind(pos=self._ajustar, size=self._ajustar, escala=self._ajustar, cor=self._cor)

    def _cor(self, *_):
        self.medalha.cor = self.cor

    def _ajustar(self, *_):
        self.medalha.pos, self.medalha.size = self.pos, self.size
        self._s.origin = self.center
        self._s.x = self._s.y = self.escala


class Celebracao(ModalView):
    """Mostra as novidades (conquista, nível, limite) uma de cada vez."""

    def __init__(self, novidades, ao_fechar=None, **kw):
        super().__init__(size_hint=(0.86, None), height=dp(360), background="", background_color=(0, 0, 0, 0),
                         overlay_color=(0.03, 0.01, 0.08, 0.78), auto_dismiss=False, **kw)
        self.fila = list(novidades)
        self.ao_fechar = ao_fechar
        caixa = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(10))
        with caixa.canvas.before:
            Color(*rgba("#22164A"))
            self._fundo = RoundedRectangle(radius=[dp(22)])
        caixa.bind(pos=lambda w, *_: setattr(self._fundo, "pos", w.pos),
                   size=lambda w, *_: setattr(self._fundo, "size", w.size))
        area = FloatLayout(size_hint_y=None, height=dp(140))
        self.medalha = MedalhaAnimada(size_hint=(None, None), size=(dp(120), dp(120)),
                                      pos_hint={"center_x": 0.5, "center_y": 0.5})
        area.add_widget(self.medalha)
        self.titulo = Label(font_size=sp(20), bold=True, color=rgba(CORES["dourado_claro"]),
                            halign="center", size_hint_y=None, height=dp(56))
        self.titulo.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
        self.msg = Label(font_size=sp(14), color=rgba(CORES["texto2"]), halign="center")
        self.msg.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
        from kivy.factory import Factory
        botao = Factory.BotaoVertis(text="Continuar", cor=rgba(CORES["dourado"]), cor_texto=rgba("#1A0E3D"))
        botao.bind(on_release=lambda *_: self.proxima())
        for w in (area, self.titulo, self.msg, botao):
            caixa.add_widget(w)
        self.add_widget(caixa)
        self.proxima()

    def proxima(self):
        if not self.fila:
            self.dismiss()
            if self.ao_fechar:
                self.ao_fechar()
            return
        n = self.fila.pop(0)
        cores = {"conquista": CORES["dourado"], "nivel": CORES["lilas"], "limite": CORES["verde"]}
        self.medalha.cor = cores.get(n["tipo"], CORES["rosa"])
        self.titulo.text = n["titulo"]
        self.msg.text = n["mensagem"]
        self.medalha.escala = 0.01
        Animation(escala=1, d=0.7, t="out_back").start(self.medalha)
