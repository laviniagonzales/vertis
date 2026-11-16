"""
TELA DE EVOLUÇÃO (a do mockup)
=============================
Lê tudo de uma vez em GET /me/resumo e distribui pelos widgets gráficos:
trilha de ascensão, moeda 3D, anel do crédito, medalhas...

O botão "Simular 1 mês" é para a APRESENTAÇÃO: a API avança o relógio
30 dias, simulando salário, compras e pagamento da fatura em dia.
"""
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import BooleanProperty, DictProperty, NumericProperty, StringProperty

import servidor
from tema import CORES, CORES_CATEGORIA
from kivy.uix.boxlayout import BoxLayout
from telas.componentes import TelaVertis, aviso

Builder.load_string("""
#:import rgba tema.rgba
#:import CORES tema.CORES
#:import servidor servidor

<MedalhaRotulo>:
    orientation: 'vertical'
    spacing: dp(2)
    Medalha:
        cor: root.cor
        ativa: root.ativa
    Label:
        text: root.rotulo
        font_size: sp(10)
        color: rgba(CORES['texto']) if root.ativa else rgba(CORES['texto2'])
        size_hint_y: None
        height: dp(26)
        text_size: self.width, None
        halign: 'center'

<CabecalhoCartao@BoxLayout>:
    icone: ''
    titulo: ''
    acao: ''
    size_hint_y: None
    height: dp(26)
    spacing: dp(10)
    Icone:
        icone: root.icone
        size_hint_x: None
        width: dp(20)
    Label:
        text: '[b]' + root.titulo + '[/b]'
        markup: True
        font_size: sp(15)
        color: rgba(CORES['texto'])
        text_size: self.size
        halign: 'left'
        valign: 'middle'
    Label:
        text: root.acao
        font_size: sp(12)
        bold: True
        color: rgba(CORES['dourado_claro'])
        size_hint_x: None
        width: self.texture_size[0]
    Icone:
        icone: 'seta'
        size_hint_x: None
        width: dp(14)
        cor: rgba(CORES['texto2'])

<PainelToque@ButtonBehavior+Painel>:
    orientation: 'vertical'
    size_hint: None, None
    pos_hint: {'center_x': .5}
    height: self.minimum_height
    spacing: dp(6)

<TelaInicio>:
    BoxLayout:
        orientation: 'vertical'
        ScrollView:
            do_scroll_x: False
            bar_width: dp(3)
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(12)
                padding: 0, 0, 0, dp(18)
                # ------------------------------------------ cabeçalho amarelo com o saldo
                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(178)
                    padding: dp(18), dp(14), dp(12), dp(18)
                    spacing: dp(2)
                    canvas.before:
                        Color:
                            rgba: rgba(CORES['amarelo'])
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [0, 0, dp(22), dp(22)]
                    BoxLayout:
                        size_hint_y: None
                        height: dp(44)
                        spacing: dp(12)
                        Widget:
                            size_hint_x: None
                            width: dp(42)
                            canvas:
                                Color:
                                    rgba: rgba(CORES['grafite'])
                                Ellipse:
                                    pos: self.x, self.center_y - dp(21)
                                    size: dp(42), dp(42)
                            Label:
                                text: root.iniciais
                                bold: True
                                font_size: sp(15)
                                color: rgba(CORES['amarelo'])
                                center: self.parent.center
                        BoxLayout:
                            orientation: 'vertical'
                            Label:
                                text: '[b]' + root.saudacao + '[/b]'
                                markup: True
                                font_size: sp(16)
                                color: rgba(CORES['texto'])
                                text_size: self.size
                                halign: 'left'
                                valign: 'bottom'
                            Label:
                                text: root.linha_conta
                                font_size: sp(11)
                                color: rgba(CORES['grafite'], 0.75)
                                text_size: self.size
                                halign: 'left'
                                valign: 'top'
                        BotaoIcone:
                            icone: 'sair'
                            size_hint_x: None
                            width: dp(40)
                            on_release: app.sair()
                    Widget:
                    Label:
                        text: 'Saldo em conta'
                        font_size: sp(13)
                        color: rgba(CORES['grafite'], 0.8)
                        size_hint_y: None
                        height: dp(20)
                        text_size: self.size
                        halign: 'left'
                        valign: 'middle'
                    BoxLayout:
                        size_hint_y: None
                        height: dp(42)
                        spacing: dp(10)
                        Label:
                            text: '[b]' + (servidor.reais(servidor.campo(root.dados, 'saldo_conta', padrao=0)) if root.mostrar_saldo else 'R$  • • • • •') + '[/b]'
                            markup: True
                            font_size: sp(28)
                            color: rgba(CORES['texto'])
                            size_hint_x: None
                            width: self.texture_size[0]
                        BotaoIcone:
                            icone: 'olho' if root.mostrar_saldo else 'olho_fechado'
                            size_hint_x: None
                            width: dp(30)
                            on_release: root.mostrar_saldo = not root.mostrar_saldo
                        Widget:
                # ------------------------------------------ atalhos
                GridLayout:
                    cols: 4
                    size_hint_y: None
                    height: dp(86)
                    padding: dp(8), 0
                    AcaoRapida:
                        icone: 'pix'
                        texto: 'Pix'
                        on_release: root.atalho_pix()
                    AcaoRapida:
                        icone: 'fatura'
                        texto: 'Fatura'
                        on_release: app.ir('cartao')
                    AcaoRapida:
                        icone: 'score'
                        texto: 'Meu score'
                        on_release: app.ir('score')
                    AcaoRapida:
                        icone: 'metas'
                        texto: 'Metas'
                        on_release: root.atalho_metas()
                # ------------------------------------------ cartão de crédito
                PainelToque:
                    width: root.width - dp(32)
                    on_release: app.ir('cartao')
                    CabecalhoCartao:
                        icone: 'cartao'
                        titulo: 'Cartão de crédito'
                        acao: 'Ver fatura'
                    Widget:
                        size_hint_y: None
                        height: dp(4)
                    TextoPequeno:
                        text: 'Limite disponível'
                    Texto:
                        text: '[b]' + servidor.reais(servidor.campo(root.dados, 'limite', 'disponivel', padrao=0)) + '[/b]'
                        font_size: sp(22)
                    BarraProgresso:
                        valor: root.fracao_disponivel
                    TextoPequeno:
                        text: 'Limite total: ' + servidor.reais(servidor.campo(root.dados, 'limite', 'total', padrao=0))
                # ------------------------------------------ crédito progressivo (trilha)
                PainelToque:
                    width: root.width - dp(32)
                    on_release: app.ir('score')
                    CabecalhoCartao:
                        icone: 'score'
                        titulo: 'Crédito progressivo'
                        acao: 'Score ' + str(servidor.campo(root.dados, 'score', padrao=0))
                    TextoPequeno:
                        text: 'Cada fatura paga em dia faz o seu limite subir.'
                    TrilhaAscensao:
                        id: trilha
                        size_hint_y: None
                        height: dp(150)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(34)
                        padding: dp(10), 0
                        canvas.before:
                            Color:
                                rgba: rgba(CORES['amarelo_suave'])
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(8)]
                        Label:
                            text: root.linha_previsto
                            markup: True
                            font_size: sp(12)
                            color: rgba(CORES['texto'])
                            text_size: self.size
                            halign: 'left'
                            valign: 'middle'
                # ------------------------------------------ Vértis Pontos
                PainelToque:
                    width: root.width - dp(32)
                    spacing: dp(8)
                    on_release: app.ir('conquistas')
                    CabecalhoCartao:
                        icone: 'pontos'
                        titulo: 'Vértis Pontos'
                        acao: 'Trocar'
                    BoxLayout:
                        size_hint_y: None
                        height: dp(48)
                        spacing: dp(12)
                        MoedaGiratoria:
                            size_hint_x: None
                            width: dp(42)
                        BoxLayout:
                            orientation: 'vertical'
                            Texto:
                                text: '[b]' + servidor.milhar(servidor.campo(root.dados, 'pontos', padrao=0)) + '[/b] pontos'
                                font_size: sp(17)
                            TextoPequeno:
                                text: servidor.milhar(servidor.campo(root.dados, 'milhas', padrao=0)) + ' milhas acumuladas'
                    Texto:
                        text: root.linha_nome
                        font_size: sp(13)
                    BarraProgresso:
                        height: dp(6)
                        valor: root.fracao_xp
                    TextoPequeno:
                        text: root.linha_xp
                        font_size: sp(11)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(40) if root.beneficio else 0
                        opacity: 1 if root.beneficio else 0
                        padding: dp(10), 0
                        canvas.before:
                            Color:
                                rgba: rgba(CORES['grafite'])
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(8)]
                        Label:
                            text: 'Benefício liberado: [b][color=#FFD24D]' + root.beneficio + '[/color][/b]'
                            markup: True
                            font_size: sp(12)
                            color: 1, 1, 1, 1
                            text_size: self.size
                            halign: 'left'
                            valign: 'middle'
                    TextoPequeno:
                        text: 'Próxima conquista: [b][color=#1F2329]' + root.proxima + '[/color][/b]'
                    BoxLayout:
                        id: medalhas
                        size_hint_y: None
                        height: dp(78)
                        padding: dp(10), dp(4)
                        spacing: dp(20)
                # ------------------------------------------ modo apresentação
                BoxLayout:
                    orientation: 'vertical'
                    size_hint: None, None
                    width: root.width - dp(32)
                    pos_hint: {'center_x': .5}
                    height: self.minimum_height
                    spacing: dp(6)
                    TextoPequeno:
                        text: 'Modo apresentação: avança o relógio 30 dias (salário, compras e fatura paga em dia).'
                        font_size: sp(11)
                    BotaoContorno:
                        text: 'Simular 1 mês de uso'
                        disabled: root.ocupado
                        opacity: 0.5 if root.ocupado else 1
                        on_release: root.simular_mes()
        BarraNavegacao:
            atual: 'inicio'
""")


class MedalhaRotulo(BoxLayout):
    cor = StringProperty(CORES["dourado"])
    ativa = BooleanProperty(True)
    rotulo = StringProperty("")


class TelaInicio(TelaVertis):
    dados = DictProperty({})
    iniciais = StringProperty("")
    linha_nome = StringProperty("")
    linha_xp = StringProperty("")
    linha_previsto = StringProperty("")
    beneficio = StringProperty("")
    proxima = StringProperty("")
    fracao_xp = NumericProperty(0)
    fracao_disponivel = NumericProperty(0)
    fracao_previsto = NumericProperty(0)
    ocupado = BooleanProperty(False)
    mostrar_saldo = BooleanProperty(True)
    saudacao = StringProperty("Olá!")
    linha_conta = StringProperty("")

    def on_pre_enter(self, *_):
        self.carregar()

    def carregar(self, depois=None):
        def recebido(r):
            self.preencher(r)
            if depois:
                depois()
        servidor.get("/me/resumo", ao_receber=recebido, ao_falhar=lambda m: aviso(m, erro=True))

    def preencher(self, r):
        nivel = r["nivel"]
        partes = r["nome"].split()
        self.iniciais = (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper()
        self.saudacao = f"Olá, {partes[0].capitalize()}"
        self.linha_conta = f"Ag/Conta {r.get('conta', '')}"
        self.linha_nome = f"Nível {nivel['ordem']}: [b]{nivel['nome']}[/b]"
        if nivel["xp_proximo_nivel"]:
            faixa = nivel["xp_proximo_nivel"] - nivel["xp_nivel_atual"]
            self.fracao_xp = (nivel["xp_total"] - nivel["xp_nivel_atual"]) / max(1, faixa)
            self.linha_xp = (f"{servidor.milhar(nivel['xp_total'])} / {servidor.milhar(nivel['xp_proximo_nivel'])} XP"
                             f" para {nivel['proximo_nivel']}  •  pontos {float(nivel['multiplicador']):.2f}x")
        else:
            self.fracao_xp, self.linha_xp = 1, f"{servidor.milhar(nivel['xp_total'])} XP — nível máximo!"
        lim = r["limite"]
        total, disp, prev = float(lim["total"]), float(lim["disponivel"]), float(lim["previsto"] or lim["total"])
        self.fracao_disponivel = disp / total if total else 0
        self.fracao_previsto = total / prev if prev else 1
        self.linha_previsto = (f"Próximo limite previsto: [b]{servidor.reais_curto(prev)}[/b] pagando em dia"
                               if prev > total else f"Limite atual: [b]{servidor.reais_curto(total)}[/b]")
        self.beneficio = r["beneficios"][0]["nome"] if r["beneficios"] else ""
        pc = r.get("proxima_conquista")
        self.proxima = (f"{pc['nome']}  ({pc['progresso_atual']}/{pc['criterio_quantidade']})"
                        if pc and pc["criterio_quantidade"] > 1 else (pc["nome"] if pc else "Todas conquistadas!"))
        self.dados = r     # dispara a atualização do KV
        self.ids.trilha.previsto = prev
        self.ids.trilha.valores = [float(p["valor"]) for p in r["trilha"]] or [total]
        self._medalhas(r["conquistas_recentes"])

    def _medalhas(self, recentes):
        from kivy.factory import Factory
        caixa = self.ids.medalhas
        caixa.clear_widgets()
        for c in recentes[:3]:
            caixa.add_widget(Factory.MedalhaRotulo(cor=CORES_CATEGORIA.get(c["categoria"], CORES["dourado"]),
                                                   rotulo=c["nome"]))
        for _ in range(3 - len(recentes[:3])):
            caixa.add_widget(Factory.MedalhaRotulo(ativa=False, rotulo="Em breve"))

    def atalho_pix(self):
        app = App.get_running_app()
        app.ir("conta")
        app.root.get_screen("conta").enviar_pix()

    def atalho_metas(self):
        app = App.get_running_app()
        app.ir("conta")
        app.root.get_screen("conta").metas()

    def simular_mes(self):
        self.ocupado = True
        aviso("Simulando 30 dias de uso...")

        def pronto(r):
            self.ocupado = False
            a, d = r["antes"], r["depois"]
            aviso(f"{servidor.data_br(r['de'])} » {servidor.data_br(r['ate'])}: "
                  f"limite {servidor.reais_curto(a['limite'])} » {servidor.reais_curto(d['limite'])}, "
                  f"score {a['score']} » {d['score']}")
            self.carregar(depois=App.get_running_app().mostrar_novidades)

        def falhou(m):
            self.ocupado = False
            aviso(m, erro=True)
        servidor.post("/demo/simular-mes-logado?comportamento=em_dia", {}, ao_receber=pronto, ao_falhar=falhou)
