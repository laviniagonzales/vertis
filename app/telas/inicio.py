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

<Chip@Painel>:
    size_hint: None, None
    padding: dp(8), dp(6)
    spacing: dp(8)
    cor_fundo: rgba('#2A1A5E', 0.92)

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

<TelaInicio>:
    BoxLayout:
        orientation: 'vertical'
        # -------------------------------------------------- cabeçalho
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            padding: dp(14), dp(6)
            spacing: dp(8)
            Widget:
                size_hint_x: None
                width: dp(26)
                canvas:
                    Color:
                        rgba: rgba(CORES['dourado'])
                    RoundedRectangle:
                        pos: self.x, self.center_y - dp(9)
                        size: dp(6), dp(10)
                        radius: [dp(2)]
                    RoundedRectangle:
                        pos: self.x + dp(8), self.center_y - dp(9)
                        size: dp(6), dp(15)
                        radius: [dp(2)]
                    RoundedRectangle:
                        pos: self.x + dp(16), self.center_y - dp(9)
                        size: dp(6), dp(21)
                        radius: [dp(2)]
            Label:
                text: '[b]VÉRTIS[/b]'
                markup: True
                font_size: sp(22)
                size_hint_x: None
                width: self.texture_size[0]
            Widget:
            BotaoContorno:
                text: 'Simular 1 mês >>'
                font_size: sp(11)
                size_hint: None, None
                size: dp(118), dp(30)
                pos_hint: {'center_y': .5}
                disabled: root.ocupado
                on_release: root.simular_mes()
            BotaoContorno:
                text: 'Sair'
                font_size: sp(11)
                size_hint: None, None
                size: dp(44), dp(30)
                pos_hint: {'center_y': .5}
                on_release: app.sair()
        # -------------------------------------------------- usuário e nível
        BoxLayout:
            size_hint_y: None
            height: dp(56)
            padding: dp(14), 0
            spacing: dp(10)
            Widget:
                size_hint_x: None
                width: dp(42)
                canvas:
                    Color:
                        rgba: rgba(servidor.campo(root.dados, 'nivel', 'cor', padrao='#A78BFA'))
                    Ellipse:
                        pos: self.x, self.center_y - dp(21)
                        size: dp(42), dp(42)
                    Color:
                        rgba: rgba('#2A1A5E')
                    Ellipse:
                        pos: self.x + dp(3), self.center_y - dp(18)
                        size: dp(36), dp(36)
                Label:
                    text: root.iniciais
                    bold: True
                    font_size: sp(15)
                    center: self.parent.center
            BoxLayout:
                orientation: 'vertical'
                padding: 0, dp(6)
                Texto:
                    text: root.linha_nome
                    font_size: sp(14)
                BarraProgresso:
                    valor: root.fracao_xp
                    cor: rgba(servidor.campo(root.dados, 'nivel', 'cor', padrao='#A78BFA'))
                TextoPequeno:
                    text: root.linha_xp
                    font_size: sp(11)
        # -------------------------------------------------- painel da trilha
        FloatLayout:
            padding: dp(10)
            canvas.before:
                Color:
                    rgba: rgba('#1A0F3D', 0.85)
                RoundedRectangle:
                    pos: self.x + dp(10), self.y + dp(4)
                    size: self.width - dp(20), self.height - dp(8)
                    radius: [dp(20)]
            TrilhaAscensao:
                id: trilha
                size_hint: None, None
                pos: self.parent.x + dp(14), self.parent.y + dp(8)
                size: self.parent.width - dp(28), self.parent.height - dp(16)
            Chip:
                pos_hint: {'x': 0.06, 'top': 0.95}
                size: dp(150), dp(56)
                MoedaGiratoria:
                    size_hint_x: None
                    width: dp(40)
                BoxLayout:
                    orientation: 'vertical'
                    TextoPequeno:
                        text: 'Pontos'
                    Texto:
                        text: '[b]' + servidor.milhar(servidor.campo(root.dados, 'pontos', padrao=0)) + '[/b] pts'
                        font_size: sp(17)
            Chip:
                pos_hint: {'right': 0.95, 'top': 0.95}
                size: dp(140), dp(52)
                BoxLayout:
                    orientation: 'vertical'
                    TextoPequeno:
                        text: 'Milhas'
                    Texto:
                        text: '[b]' + servidor.milhar(servidor.campo(root.dados, 'milhas', padrao=0)) + '[/b] mi'
                        font_size: sp(17)
            Chip:
                pos_hint: {'right': 0.95, 'y': 0.42}
                size: dp(168), dp(58)
                opacity: 1 if root.beneficio else 0
                cor_fundo: rgba('#F5B83D', 0.95)
                cor_borda: rgba('#FFE29A', 1)
                BoxLayout:
                    orientation: 'vertical'
                    Label:
                        text: '[b]' + root.beneficio + '[/b]'
                        markup: True
                        color: rgba('#2A1460')
                        font_size: sp(13)
                        text_size: self.size
                        valign: 'middle'
                    Label:
                        text: '[b]LIBERADO![/b]'
                        markup: True
                        color: rgba('#7C2D12')
                        font_size: sp(11)
                        text_size: self.size
                        valign: 'middle'
            Chip:
                id: chip_credito
                pos_hint: {'right': 0.95, 'y': 0.06}
                size: dp(214), dp(66)
                on_touch_down: app.ir('score') if self.collide_point(*args[1].pos) else None
                AnelCredito:
                    size_hint_x: None
                    width: dp(50)
                    fracao: root.fracao_disponivel
                BoxLayout:
                    orientation: 'vertical'
                    TextoPequeno:
                        text: 'Crédito Progressivo  >'
                    Texto:
                        text: 'Limite: [b]' + servidor.reais_curto(servidor.campo(root.dados, 'limite', 'total', padrao=0)) + '[/b]'
                        font_size: sp(15)
                    BarraProgresso:
                        height: dp(5)
                        valor: root.fracao_previsto
                        cor: rgba(CORES['rosa'])
                    TextoPequeno:
                        text: root.linha_previsto
                        font_size: sp(10)
        # -------------------------------------------------- próxima conquista
        Painel:
            size_hint_y: None
            height: dp(56)
            padding: dp(14), dp(6)
            spacing: 0
            orientation: 'vertical'
            TextoPequeno:
                text: 'Próxima Conquista:'
                halign: 'center'
            Texto:
                text: '[b][color=#FFE29A]' + root.proxima + '[/color][/b]'
                halign: 'center'
                font_size: sp(16)
        # -------------------------------------------------- medalhas
        BoxLayout:
            id: medalhas
            size_hint_y: None
            height: dp(82)
            padding: dp(24), dp(4)
            spacing: dp(24)
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
        self.linha_nome = f"[b]{r['nome']}[/b]  •  [color=#A78BFA]Nível {nivel['ordem']} ({nivel['nome']})[/color]"
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
        self.linha_previsto = (f"Próximo: {servidor.reais_curto(prev)} pagando em dia" if prev > total
                               else f"Disponível: {servidor.reais_curto(disp)}")
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
