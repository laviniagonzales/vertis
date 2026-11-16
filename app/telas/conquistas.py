"""
TELA DE CONQUISTAS — níveis, conquistas, benefícios e resgate de pontos
"""
from kivy.app import App
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import BooleanProperty, DictProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout

import servidor
from tema import CORES, CORES_CATEGORIA
from telas.componentes import Painel, TelaVertis, aviso
from telas.formulario import abrir_formulario, numero

Builder.load_string("""
#:import rgba tema.rgba
#:import CORES tema.CORES
#:import servidor servidor

<NivelMini>:
    orientation: 'vertical'
    spacing: dp(2)
    canvas.before:
        Color:
            rgba: rgba(CORES['dourado'], 0.9 if root.atual else 0)
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(10))
            width: 1.4
    Medalha:
        cor: root.cor
        ativa: root.ativa
    Label:
        text: root.nome
        font_size: sp(9)
        bold: root.atual
        size_hint_y: None
        height: dp(24)
        text_size: self.width, None
        halign: 'center'
        color: rgba(CORES['texto']) if root.ativa else rgba(CORES['texto2'])
    Label:
        text: root.xp
        font_size: sp(8)
        size_hint_y: None
        height: dp(12)
        color: rgba(CORES['texto2'])

<LinhaConquista>:
    size_hint_y: None
    height: dp(84)
    spacing: dp(10)
    Medalha:
        size_hint_x: None
        width: dp(48)
        cor: root.cor
        ativa: root.ativa
    BoxLayout:
        orientation: 'vertical'
        spacing: dp(3)
        Texto:
            text: '[b]' + root.nome + '[/b]' + ('   [color=#1E8E4E]conquistada[/color]' if root.ativa else '')
        TextoPequeno:
            text: root.descricao
            font_size: sp(11)
        BarraProgresso:
            height: dp(6)
            valor: root.progresso
            cor: rgba(root.cor)
        TextoPequeno:
            text: root.detalhe
            font_size: sp(10)
            color: rgba(CORES['dourado_claro'])

<TelaConquistas>:
    BoxLayout:
        orientation: 'vertical'
        BarraTopo:
            titulo: 'Pontos e conquistas'
            BotaoVertis:
                text: 'Trocar pontos'
                font_size: sp(13)
                size_hint: None, None
                size: dp(122), dp(36)
                pos_hint: {'center_y': .5}
                on_release: root.trocar()
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: dp(150)
            padding: dp(16), dp(12), dp(16), dp(4)
            spacing: dp(6)
            Painel:
                id: niveis
                orientation: 'horizontal'
                padding: dp(6), dp(8)
                spacing: dp(4)
            TextoPequeno:
                text: root.saldos
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: lista
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: dp(14), dp(6)
                spacing: dp(8)
        BarraNavegacao:
            atual: 'conquistas'
""")


class NivelMini(BoxLayout):
    cor = StringProperty("#F5B700")
    ativa = BooleanProperty(True)
    atual = BooleanProperty(False)
    nome = StringProperty("")
    xp = StringProperty("")


class LinhaConquista(Painel):
    cor = StringProperty("#F5B700")
    ativa = BooleanProperty(False)
    nome = StringProperty("")
    descricao = StringProperty("")
    progresso = NumericProperty(0)
    detalhe = StringProperty("")


class TelaConquistas(TelaVertis):
    resumo = DictProperty({})
    saldos = StringProperty("")

    def on_pre_enter(self, *_):
        servidor.get("/me/resumo", ao_receber=self._resumo)

    def _resumo(self, r):
        self.resumo = r
        self.saldos = (f"Saldo: {servidor.milhar(r['pontos'])} pontos  •  {servidor.milhar(r['milhas'])} milhas  •  "
                       f"{r['sequencia_dias']} dia(s) seguidos no app")
        servidor.get("/gamificacao/conquistas", ao_receber=self._preencher, ao_falhar=lambda m: aviso(m, erro=True))

    def _preencher(self, r):
        atual = self.resumo["nivel"]["ordem"]
        caixa = self.ids.niveis
        caixa.clear_widgets()
        for n in r["niveis"]:
            caixa.add_widget(Factory.NivelMini(cor=n["cor_hex"], ativa=n["ordem"] <= atual, atual=n["ordem"] == atual,
                                               nome=n["nome"], xp=f"{servidor.milhar(n['xp_minimo'])} XP"))
        lista = self.ids.lista
        lista.clear_widgets()
        if self.resumo["beneficios"]:
            lista.add_widget(Factory.Texto(text="[b]Meus benefícios[/b]"))
            for b in self.resumo["beneficios"]:
                extra = f"  •  código {b['codigo_voucher']}" if b.get("codigo_voucher") else ""
                usos = f"  •  {b['usos_restantes']} uso(s) no mês" if b.get("usos_restantes") else ""
                lista.add_widget(Factory.TextoPequeno(text=f"[color=#D99A00]•[/color] {b['nome']}{extra}{usos}"))
        lista.add_widget(Factory.Texto(text="[b]Conquistas[/b]"))
        for c in r["conquistas"]:
            premio = f"+{servidor.milhar(c['pontos_recompensa'])} pontos"
            if c["beneficio"]:
                premio += f"  •  libera {c['beneficio']}"
            lista.add_widget(Factory.LinhaConquista(
                cor=CORES_CATEGORIA.get(c["categoria"], CORES["dourado"]), ativa=c["status"] == "conquistada",
                nome=c["nome"], descricao=c["descricao"] or "",
                progresso=c["progresso_atual"] / max(1, c["criterio_quantidade"]),
                detalhe=f"{c['progresso_atual']}/{c['criterio_quantidade']}   •   {premio}"))

    def trocar(self):
        pontos = self.resumo.get("pontos", 0)
        abrir_formulario("Trocar pontos por cashback", [("qtd", "Quantos pontos?", "numero", str(min(pontos, 1000)))],
                         "Trocar", lambda v: servidor.post(
                             "/gamificacao/resgatar", {"tipo": "cashback", "quantidade": int(numero(v["qtd"]))},
                             ao_receber=lambda r: (aviso(f"{servidor.reais(r['valor_reais'])} de cashback na sua conta!"),
                                                   self.on_pre_enter()),
                             ao_falhar=lambda m: aviso(m, erro=True)),
                         explicacao=f"Você tem {servidor.milhar(pontos)} pontos. 100 pontos = R$ 1,00 na conta.")
