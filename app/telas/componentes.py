"""
COMPONENTES REUTILIZADOS POR TODAS AS TELAS
==========================================
O visual é descrito em "KV" (a linguagem de layout do Kivy, parecida com CSS)
e o comportamento em Python.

Identidade visual: fundo cinza bem claro, cartões brancos, amarelo da marca
nos botões principais e cinza-grafite nos ícones e contornos.
"""
from kivy.animation import Animation
from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, PopMatrix, PushMatrix, RoundedRectangle, Scale
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ColorProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput
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
    padding: dp(16)
    spacing: dp(6)
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.035
        RoundedRectangle:
            pos: self.x, self.y - dp(2)
            size: self.size
            radius: [dp(14)]
        Color:
            rgba: self.cor_fundo
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]
        Color:
            rgba: self.cor_borda
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(14))
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

<Rotulo@TextoPequeno>:
    font_size: sp(12)
    bold: True
    color: rgba(CORES['grafite'])
    padding: 0, dp(4), 0, 0

<BotaoVertis>:
    color: self.cor_texto
    disabled_color: self.cor_texto[0], self.cor_texto[1], self.cor_texto[2], 0.6
    font_size: sp(15)
    bold: True
    size_hint_y: None
    height: dp(48)
    canvas.before:
        Color:
            rgba: (self.cor[0] * 0.88, self.cor[1] * 0.88, self.cor[2] * 0.88, 1) if self.state == 'down' else self.cor
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]

<BotaoSecundario@BotaoVertis>:
    cor: rgba(CORES['cinza_claro'])
    cor_texto: rgba(CORES['grafite'])

<BotaoContorno@ButtonBehavior+Label>:
    color: rgba(CORES['grafite'])
    font_size: sp(14)
    bold: True
    size_hint_y: None
    height: dp(44)
    canvas.before:
        Color:
            rgba: rgba(CORES['cinza_claro'], 1 if self.state == 'down' else 0)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]
        Color:
            rgba: rgba(CORES['cinza_medio'])
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(10))
            width: 1.1

<BotaoLink@ButtonBehavior+Label>:
    color: rgba(CORES['grafite'], 0.6 if self.state == 'down' else 1)
    font_size: sp(13)
    bold: True
    size_hint_y: None
    height: dp(36)

<Campo>:
    multiline: False
    write_tab: False
    size_hint_y: None
    height: dp(48)
    padding: dp(14), dp(14)
    background_normal: ''
    background_active: ''
    background_disabled_normal: ''
    background_color: 0, 0, 0, 0
    foreground_color: rgba(CORES['texto'])
    disabled_foreground_color: rgba(CORES['texto2'])
    hint_text_color: rgba(CORES['texto2'], 0.75)
    cursor_color: rgba(CORES['grafite'])
    selection_color: rgba(CORES['amarelo'], 0.35)
    font_size: sp(15)
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]
        # devolve a cor do texto (o fundo branco acima tinha trocado a cor ativa)
        Color:
            rgba: self.disabled_foreground_color if self.disabled else (self.hint_text_color if not self.text else self.foreground_color)
    canvas.after:
        Color:
            rgba: rgba(CORES['amarelo']) if self.focus else rgba(CORES['cinza_medio'])
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(10))
            width: 1.6 if self.focus else 1

<Opcoes@Spinner>:
    size_hint_y: None
    height: dp(48)
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    color: rgba(CORES['texto'])
    font_size: sp(15)
    halign: 'left'
    valign: 'middle'
    text_size: self.width - dp(28), None
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]
        Color:
            rgba: rgba(CORES['cinza_medio'])
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(10))
            width: 1
        Color:
            rgba: rgba(CORES['grafite'])
        Line:
            points: self.right - dp(24), self.center_y + dp(3), self.right - dp(19), self.center_y - dp(2), self.right - dp(14), self.center_y + dp(3)
            width: 1.4

<SpinnerOption>:
    background_normal: ''
    background_down: ''
    background_color: 1, 1, 1, 1
    color: rgba(CORES['texto'])
    height: dp(44)
    canvas.after:
        Color:
            rgba: rgba(CORES['borda'])
        Line:
            points: self.x, self.y, self.right, self.y

<Caixa>:
    size_hint: None, None
    size: dp(22), dp(22)
    canvas:
        Color:
            rgba: rgba(CORES['amarelo']) if self.ativo else (1, 1, 1, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(5)]
        Color:
            rgba: rgba(CORES['amarelo']) if self.ativo else rgba(CORES['cinza_medio'])
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(5))
            width: 1.2
        Color:
            rgba: rgba(CORES['grafite'], 1 if self.ativo else 0)
        Line:
            points: self.x + dp(5), self.center_y, self.x + dp(9), self.y + dp(6), self.right - dp(5), self.top - dp(6)
            width: 1.8

<Consentimento>:
    size_hint_y: None
    height: max(dp(44), rotulo.texture_size[1] + dp(16))
    spacing: dp(12)
    Caixa:
        ativo: root.ativo
        pos_hint: {'center_y': .5}
    Label:
        id: rotulo
        text: root.texto
        color: rgba(CORES['texto'])
        font_size: sp(13)
        text_size: self.width, None
        halign: 'left'
        valign: 'middle'

<BarraProgresso>:
    size_hint_y: None
    height: dp(8)
    canvas:
        Color:
            rgba: rgba(CORES['cinza_claro'])
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

<BarraTopo>:
    size_hint_y: None
    height: dp(56)
    padding: dp(6) if root.voltar else dp(16), 0, dp(16), 0
    spacing: dp(6)
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: rgba(CORES['borda'])
        Line:
            points: self.x, self.y, self.right, self.y
    BotaoIcone:
        icone: 'voltar'
        size_hint: None, None
        size: (dp(40), dp(40)) if root.voltar else (0, dp(40))
        opacity: 1 if root.voltar else 0
        disabled: not root.voltar
        pos_hint: {'center_y': .5}
        on_release: root.ao_voltar()
    Label:
        text: root.titulo
        bold: True
        font_size: sp(18)
        color: rgba(CORES['texto'])
        text_size: self.size
        halign: 'left'
        valign: 'middle'

<AcaoRapida>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(86)
    spacing: dp(6)
    AnchorLayout:
        size_hint_y: None
        height: dp(56)
        Widget:
            size_hint: None, None
            size: dp(56), dp(56)
            canvas:
                Color:
                    rgba: rgba(CORES['amarelo_suave']) if root.state != 'down' else rgba(CORES['amarelo'], 0.45)
                Ellipse:
                    pos: self.pos
                    size: self.size
            Icone:
                icone: root.icone
                cor: rgba(CORES['grafite'])
                pos: self.parent.x + dp(16), self.parent.y + dp(16)
                size: dp(24), dp(24)
    Label:
        text: root.texto
        font_size: sp(12)
        color: rgba(CORES['texto'])
        text_size: self.width, None
        halign: 'center'
        valign: 'top'

<BotaoNav>:
    orientation: 'vertical'
    padding: 0, dp(8), 0, dp(6)
    spacing: dp(2)
    canvas.before:
        Color:
            rgba: rgba(CORES['amarelo'], 1 if self.ativo else 0)
        RoundedRectangle:
            pos: self.center_x - dp(16), self.top - dp(3)
            size: dp(32), dp(3)
            radius: [dp(2)]
    Icone:
        icone: root.icone
        cor: rgba(CORES['grafite']) if root.ativo else rgba(CORES['texto2'], 0.85)
    Label:
        text: root.texto
        font_size: sp(11)
        bold: root.ativo
        color: rgba(CORES['texto']) if root.ativo else rgba(CORES['texto2'])
        size_hint_y: None
        height: dp(16)

<BarraNavegacao>:
    size_hint_y: None
    height: dp(62)
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        Rectangle:
            pos: self.pos
            size: self.size
        Color:
            rgba: rgba(CORES['borda'])
        Line:
            points: self.x, self.top, self.right, self.top
""")


class TelaVertis(Screen):
    """Tela base: fundo cinza-claro (degradê bem suave, rasterizado em cg/raster.py)."""


# Classes com propriedades próprias são declaradas em Python (com valor padrão);
# o visual delas está no KV acima.
class Painel(BoxLayout):
    cor_fundo = ColorProperty(rgba(CORES["card"]))
    cor_borda = ColorProperty(rgba(CORES["borda"]))


class BotaoVertis(ButtonBehavior, Label):
    cor = ColorProperty(rgba(CORES["amarelo"]))
    cor_texto = ColorProperty(rgba(CORES["texto"]))


class BarraProgresso(Widget):
    valor = NumericProperty(0)
    cor = ColorProperty(rgba(CORES["amarelo"]))


class Caixa(Widget):
    """Caixinha de marcar (checkbox) no estilo do app."""
    ativo = BooleanProperty(False)


class Consentimento(ButtonBehavior, BoxLayout):
    """Linha com caixinha + texto. Tocar em qualquer lugar da linha marca/desmarca."""
    texto = StringProperty("")
    ativo = BooleanProperty(False)

    def on_release(self):
        self.ativo = not self.ativo


# ---------------------------------------------------------------- ícones vetoriais
class Icone(Widget):
    """Ícones desenhados com linhas (sem imagens nem fontes de ícones).
    As coordenadas de cada ícone estão num quadrado de -1 a 1 e são
    ESCALADAS e TRANSLADADAS para o tamanho do widget (transformação 2D)."""
    icone = StringProperty("")
    cor = ColorProperty(rgba(CORES["grafite"]))

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._desenhar, size=self._desenhar, icone=self._desenhar, cor=self._desenhar)

    def _desenhar(self, *_):
        self.canvas.clear()
        s = min(self.width, self.height) / 2 * 0.82
        if s <= 1:
            return
        cx, cy = self.center
        e = max(1.0, dp(1.6))

        def P(*pts):
            r = []
            for x, y in pts:
                r += [cx + x * s, cy + y * s]
            return r

        def L(*pts, fechar=False):
            Line(points=P(*pts), width=e, close=fechar, joint="round", cap="round")

        n = self.icone
        with self.canvas:
            Color(*self.cor)
            if n == "inicio":
                L((-0.95, 0.0), (0, 0.85), (0.95, 0.0))
                L((-0.65, 0.25), (-0.65, -0.85), (0.65, -0.85), (0.65, 0.25))
                L((-0.2, -0.85), (-0.2, -0.3), (0.2, -0.3), (0.2, -0.85))
            elif n == "conta":
                L((-0.95, 0.35), (0, 0.9), (0.95, 0.35), fechar=True)
                for x in (-0.6, 0, 0.6):
                    L((x, 0.2), (x, -0.5))
                L((-0.95, -0.75), (0.95, -0.75))
            elif n == "cartao":
                Line(rounded_rectangle=(cx - 0.95 * s, cy - 0.65 * s, 1.9 * s, 1.3 * s, 0.18 * s), width=e)
                L((-0.95, 0.25), (0.95, 0.25))
                L((-0.6, -0.3), (-0.15, -0.3))
            elif n == "pontos":
                import math
                pts = []
                for i in range(10):
                    a = math.pi / 2 + i * math.pi / 5
                    r = 0.95 if i % 2 == 0 else 0.42
                    pts.append((math.cos(a) * r, math.sin(a) * r - 0.05))
                L(*pts, fechar=True)
            elif n == "lab":
                L((-0.45, 0.85), (0.45, 0.85))
                L((-0.25, 0.85), (-0.25, 0.2), (-0.8, -0.8), (0.8, -0.8), (0.25, 0.2), (0.25, 0.85))
                L((-0.5, -0.35), (0.5, -0.35))
            elif n == "pix":
                L((0, 0.95), (0.95, 0), (0, -0.95), (-0.95, 0), fechar=True)
                L((0, 0.4), (0.4, 0), (0, -0.4), (-0.4, 0), fechar=True)
            elif n == "fatura":
                L((-0.65, -0.9), (0.65, -0.9), (0.65, 0.9), (-0.65, 0.9), fechar=True)
                for y in (0.45, 0.1, -0.25):
                    L((-0.32, y), (0.32, y))
                L((-0.32, -0.55), (0.05, -0.55))
            elif n == "score":
                Line(circle=(cx, cy - 0.25 * s, 0.9 * s, -90, 90), width=e, cap="round")
                L((0, -0.25), (0.45, 0.35))
                Ellipse(pos=(cx - 0.12 * s, cy - 0.37 * s), size=(0.24 * s, 0.24 * s))
            elif n == "metas":
                Line(circle=(cx, cy, 0.9 * s), width=e)
                Line(circle=(cx, cy, 0.5 * s), width=e)
                Ellipse(pos=(cx - 0.14 * s, cy - 0.14 * s), size=(0.28 * s, 0.28 * s))
            elif n == "receber":
                L((0, 0.9), (0, -0.2))
                L((-0.4, 0.2), (0, -0.2), (0.4, 0.2))
                L((-0.9, -0.3), (-0.9, -0.85), (0.9, -0.85), (0.9, -0.3))
            elif n == "dinheiro":
                Line(rounded_rectangle=(cx - 0.95 * s, cy - 0.6 * s, 1.9 * s, 1.2 * s, 0.12 * s), width=e)
                Line(circle=(cx, cy, 0.3 * s), width=e)
            elif n in ("olho", "olho_fechado"):
                Line(ellipse=(cx - 0.95 * s, cy - 0.55 * s, 1.9 * s, 1.1 * s), width=e)
                Ellipse(pos=(cx - 0.28 * s, cy - 0.28 * s), size=(0.56 * s, 0.56 * s))
                if n == "olho_fechado":
                    L((-0.85, -0.85), (0.85, 0.85))
            elif n == "sair":
                L((0.2, 0.85), (-0.75, 0.85), (-0.75, -0.85), (0.2, -0.85))
                L((-0.2, 0), (0.9, 0))
                L((0.55, 0.35), (0.9, 0), (0.55, -0.35))
            elif n == "voltar":
                L((0.3, 0.65), (-0.35, 0), (0.3, -0.65))
            elif n == "seta":
                L((-0.3, 0.65), (0.35, 0), (-0.3, -0.65))
            elif n == "girar":
                Line(circle=(cx, cy, 0.75 * s, 30, 330), width=e, cap="round")
                L((0.05, 0.95), (0.38, 0.68), (0.05, 0.4))
            elif n == "cadeado":
                Line(rounded_rectangle=(cx - 0.7 * s, cy - 0.9 * s, 1.4 * s, 1.1 * s, 0.15 * s), width=e)
                Line(circle=(cx, cy + 0.2 * s, 0.45 * s, -90, 90), width=e)
                L((-0.45, 0.2), (-0.45, 0.0))
                L((0.45, 0.2), (0.45, 0.0))
            elif n == "sacola":
                L((-0.8, 0.4), (0.8, 0.4), (0.65, -0.9), (-0.65, -0.9), fechar=True)
                Line(circle=(cx, cy + 0.4 * s, 0.38 * s, -90, 90), width=e)
            elif n == "escudo":
                L((0, 0.95), (0.8, 0.6), (0.7, -0.2), (0, -0.95), (-0.7, -0.2), (-0.8, 0.6), fechar=True)
                L((-0.3, 0.0), (-0.05, -0.28), (0.38, 0.25))


class BotaoIcone(ButtonBehavior, Icone):
    pass


class AcaoRapida(ButtonBehavior, BoxLayout):
    """Botão redondo com ícone + legenda (atalhos da tela inicial)."""
    icone = StringProperty("")
    texto = StringProperty("")


class BarraTopo(BoxLayout):
    titulo = StringProperty("")
    voltar = BooleanProperty(False)
    destino_voltar = StringProperty("")

    def ao_voltar(self):
        app = App.get_running_app()
        app.ir(self.destino_voltar or app.tela_anterior or "inicio", "right")


class BotaoNav(ButtonBehavior, BoxLayout):
    ativo = BooleanProperty(False)
    destino = StringProperty("")
    icone = StringProperty("")
    texto = StringProperty("")


class BarraNavegacao(BoxLayout):
    ITENS = [("inicio", "Início", "inicio"), ("conta", "Conta", "conta"), ("cartao", "Cartão", "cartao"),
             ("conquistas", "Pontos", "pontos"), ("lab", "Lab CG", "lab")]
    atual = StringProperty("inicio")

    def __init__(self, **kw):
        super().__init__(**kw)
        for destino, nome, icone in self.ITENS:
            b = BotaoNav(texto=nome, destino=destino, icone=icone, ativo=(destino == self.atual))
            b.bind(on_release=lambda btn: App.get_running_app().ir(btn.destino))
            self.add_widget(b)
        self.bind(atual=self._marcar)

    def _marcar(self, *_):
        for b in self.children:
            b.ativo = (b.destino == self.atual)


# ---------------------------------------------------------------- campos com máscara
class Campo(TextInput):
    """Campo de texto padrão do app (visual no KV acima)."""


class CampoMascara(Campo):
    """Campo que formata sozinho enquanto o cliente digita.
    Na máscara, '#' é um dígito; os outros caracteres (/ . - ( ) espaço)
    são colocados automaticamente. Ex.: '##/##/####' → 14/03/1998.

    O campo guarda só os DÍGITOS e redesenha o texto a cada tecla,
    colocando o cursor logo depois do último dígito digitado."""
    mascara = StringProperty("")

    def __init__(self, **kw):
        kw.setdefault("input_type", "number")
        super().__init__(**kw)
        self.bind(text=self._formatar)
        self._formatar()

    @property
    def limite(self) -> int:
        return self.mascara.count("#")

    @property
    def digitos(self) -> str:
        return "".join(c for c in self.text if c.isdigit())

    @property
    def completo(self) -> bool:
        return len(self.digitos) == self.limite

    def _aplicar(self, d: str) -> str:
        saida, i = "", 0
        for ch in self.mascara:
            if i >= len(d):
                break                 # separador só aparece quando vem um dígito depois dele
            if ch == "#":
                saida += d[i]
                i += 1
            else:
                saida += ch
        return saida

    def _posicao_apos(self, texto: str, n: int) -> int:
        """Índice no texto logo depois do n-ésimo dígito."""
        if n <= 0:
            return 0
        vistos = 0
        for i, c in enumerate(texto):
            if c.isdigit():
                vistos += 1
                if vistos == n:
                    return i + 1
        return len(texto)

    def _digitos_antes_do_cursor(self) -> int:
        return sum(c.isdigit() for c in self.text[:self.cursor_index()])

    def _mostrar(self, d: str, n_cursor: int):
        texto = self._aplicar(d[:self.limite])
        self.text = texto
        self.cursor = self.get_cursor_from_index(self._posicao_apos(texto, n_cursor))

    def insert_text(self, substring, from_undo=False):
        if self.selection_text:
            self.delete_selection()
        novos = "".join(c for c in substring if c.isdigit())
        d, k = self.digitos, self._digitos_antes_do_cursor()
        novos = novos[:max(0, self.limite - len(d))]
        if novos:
            self._mostrar(d[:k] + novos + d[k:], k + len(novos))

    def do_backspace(self, from_undo=False, mode="bkspc"):
        if self.selection_text:
            self.delete_selection()
            return
        d, k = self.digitos, self._digitos_antes_do_cursor()
        if k:                          # apaga o dígito antes do cursor, pulando "/", ".", "-"
            self._mostrar(d[:k - 1] + d[k:], k - 1)

    def _formatar(self, *_):           # texto colocado pelo código (ex.: CPF do cliente demo)
        texto = self._aplicar(self.digitos[:self.limite])
        if texto != self.text:
            self.text = texto
            self.cursor = self.get_cursor_from_index(len(texto))


class CampoData(CampoMascara):
    mascara = StringProperty("##/##/####")


class CampoCPF(CampoMascara):
    mascara = StringProperty("###.###.###-##")


class CampoTelefone(CampoMascara):
    mascara = StringProperty("(##) #####-####")


class CampoDinheiro(Campo):
    """Valor em reais digitado como nos apps de banco: os números entram
    pela direita (2 → R$ 0,02 → R$ 0,25 → R$ 2,50 → R$ 25,00)."""

    def __init__(self, **kw):
        kw.setdefault("input_type", "number")
        super().__init__(**kw)
        self.bind(text=self._formatar)

    @property
    def _digitos(self) -> str:
        return "".join(c for c in self.text if c.isdigit()).lstrip("0")

    @property
    def valor(self) -> float:
        d = self._digitos
        return int(d) / 100 if d else 0.0

    def definir(self, valor):
        self.text = f"{int(round(float(valor or 0) * 100))}" if valor else ""

    @staticmethod
    def _aplicar(d: str) -> str:
        d = d.lstrip("0")[:11]
        if not d:
            return ""
        return "R$ " + f"{int(d) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _mostrar(self, d: str):
        self.text = self._aplicar(d)
        self.cursor = self.get_cursor_from_index(len(self.text))

    def insert_text(self, substring, from_undo=False):
        if self.selection_text:
            self.delete_selection()
        novos = "".join(c for c in substring if c.isdigit())
        if novos:
            self._mostrar(self._digitos + novos)

    def do_backspace(self, from_undo=False, mode="bkspc"):
        if self.selection_text:
            self.delete_selection()
            return
        self._mostrar(self._digitos[:-1])

    def _formatar(self, *_):
        texto = self._aplicar("".join(c for c in self.text if c.isdigit()))
        if texto != self.text:
            self.text = texto
            self.cursor = self.get_cursor_from_index(len(texto))


# ---------------------------------------------------------------- aviso rápido (toast)
def aviso(texto, erro=False):
    rot = Label(text=texto, font_size=sp(13), color=(1, 1, 1, 1), size_hint=(None, None),
                halign="center", valign="middle")
    rot.text_size = (Window.width * 0.80, None)
    rot.texture_update()
    rot.size = (Window.width * 0.88, rot.texture_size[1] + dp(24))
    rot.pos = ((Window.width - rot.width) / 2, dp(78))
    with rot.canvas.before:
        Color(*rgba(CORES["vermelho"] if erro else CORES["grafite"], 0.97))
        RoundedRectangle(pos=rot.pos, size=rot.size, radius=[dp(10)])
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
                         overlay_color=(0.08, 0.09, 0.11, 0.55), auto_dismiss=False, **kw)
        self.fila = list(novidades)
        self.ao_fechar = ao_fechar
        caixa = BoxLayout(orientation="vertical", padding=dp(22), spacing=dp(10))
        with caixa.canvas.before:
            Color(1, 1, 1, 1)
            self._fundo = RoundedRectangle(radius=[dp(18)])
        caixa.bind(pos=lambda w, *_: setattr(self._fundo, "pos", w.pos),
                   size=lambda w, *_: setattr(self._fundo, "size", w.size))
        area = FloatLayout(size_hint_y=None, height=dp(140))
        self.medalha = MedalhaAnimada(size_hint=(None, None), size=(dp(120), dp(120)),
                                      pos_hint={"center_x": 0.5, "center_y": 0.5})
        area.add_widget(self.medalha)
        self.titulo = Label(font_size=sp(20), bold=True, color=rgba(CORES["texto"]),
                            halign="center", size_hint_y=None, height=dp(56))
        self.titulo.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
        self.msg = Label(font_size=sp(14), color=rgba(CORES["texto2"]), halign="center")
        self.msg.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
        botao = BotaoVertis(text="Continuar")
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
        cores = {"conquista": CORES["amarelo"], "nivel": CORES["rosa"], "limite": CORES["verde"]}
        self.medalha.cor = cores.get(n["tipo"], CORES["amarelo"])
        self.titulo.text = n["titulo"]
        self.msg.text = n["mensagem"]
        self.medalha.escala = 0.01
        Animation(escala=1, d=0.7, t="out_back").start(self.medalha)
