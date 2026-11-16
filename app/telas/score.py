"""
TELA "MEU SCORE" — transparência (um dos valores da Vértis)
==========================================================
Mostra a nota de 0 a 1000 e OS MOTIVOS dela (fatores positivos e negativos),
o histórico do limite, e dá acesso a Open Finance e empréstimo.
O medidor é um anel de 240° rasterizado com antialiasing (cg/raster.py).
"""
from kivy.app import App
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import NumericProperty, StringProperty

import servidor
from telas.componentes import TelaVertis, aviso
from telas.formulario import abrir_formulario, numero

RISCO = {"muito_baixo": "Risco muito baixo", "baixo": "Risco baixo", "medio": "Risco médio",
         "alto": "Risco alto", "muito_alto": "Risco muito alto"}
MOTIVO = {"aumento_automatico": "aumento automático", "solicitacao_cliente": "pedido do cliente",
          "reducao_risco": "redução por risco", "subida_nivel": "bônus de nível", "open_finance": "Open Finance"}

Builder.load_string("""
#:import rgba tema.rgba
#:import CORES tema.CORES

<TelaScore>:
    BoxLayout:
        orientation: 'vertical'
        BarraTopo:
            titulo: 'Meu score'
            voltar: True
        FloatLayout:
            size_hint_y: None
            height: dp(190)
            AnelCredito:
                size_hint: None, None
                size: dp(180), dp(180)
                pos_hint: {'center_x': .5, 'center_y': .5}
                fracao: root.score / 1000.0
                inicio: 210
                abertura: 240
                espessura: dp(14)
                cores: ['#D33A2C', '#F5B700', '#1E8E4E']
            Label:
                text: '[b]' + str(root.score) + '[/b]'
                markup: True
                color: rgba(CORES['texto'])
                font_size: sp(44)
                pos_hint: {'center_x': .5, 'center_y': .56}
                size_hint: None, None
                size: dp(160), dp(56)
            Label:
                text: 'de 1000  •  ' + root.risco
                font_size: sp(12)
                color: rgba(CORES['texto2'])
                pos_hint: {'center_x': .5, 'center_y': .1}
                size_hint: None, None
                size: dp(220), dp(20)
        BoxLayout:
            size_hint_y: None
            height: dp(46)
            padding: dp(16), 0
            spacing: dp(10)
            BotaoVertis:
                text: 'Open Finance'
                on_release: root.open_finance()
            BotaoSecundario:
                text: 'Empréstimo'
                on_release: root.emprestimo()
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: lista
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: dp(16), dp(10)
                spacing: dp(6)
""")


class TelaScore(TelaVertis):
    score = NumericProperty(0)
    risco = StringProperty("")

    def on_pre_enter(self, *_):
        servidor.get("/credito/score", ao_receber=self._preencher, ao_falhar=lambda m: aviso(m, erro=True))

    def _preencher(self, r):
        atual, perfil = r["atual"], r["perfil"]
        self.score = atual["score_interno"]
        self.risco = RISCO.get(perfil["perfil_risco"], "")
        lista = self.ids.lista
        lista.clear_widgets()
        T, P = Factory.Texto, Factory.TextoPequeno
        lista.add_widget(T(text="[b]O que ajudou sua nota[/b]"))
        for f in atual["fatores_positivos"] or []:
            lista.add_widget(P(text=f"[color=#1E8E4E][b]+{f['pontos']}[/b][/color]   {f['fator']}"))
        if atual["fatores_negativos"]:
            lista.add_widget(T(text="[b]O que puxou para baixo[/b]"))
            for f in atual["fatores_negativos"]:
                lista.add_widget(P(text=f"[color=#D33A2C][b]{f['pontos']}[/b][/color]   {f['fator']}"))
        lista.add_widget(P(text=f"(todo cliente começa com 300 pontos • modelo {atual['versao_modelo']})"))
        lista.add_widget(T(text="[b]Seu perfil[/b]"))
        lista.add_widget(P(text=f"Renda comprovada: {servidor.reais(perfil['renda_media_comprovada'])}/mês  •  "
                                f"Gasto médio: {servidor.reais(perfil['gasto_medio_mensal'])}/mês"))
        lista.add_widget(P(text=f"Comprometimento da renda: {float(perfil['comprometimento_renda'] or 0):.0f}%  •  "
                                f"Faturas em dia: {perfil['faturas_pagas_em_dia']}  •  Atrasos: {perfil['faturas_atrasadas']}"))
        lista.add_widget(P(text=f"Meses de conta: {perfil['meses_de_relacionamento']}  •  "
                                f"Open Finance: {'conectado' if perfil['tem_open_finance'] else 'não conectado'}"))
        lista.add_widget(T(text="[b]Evolução do limite[/b]"))
        for h in reversed(r["historico_limite"]):
            lista.add_widget(P(text=f"{servidor.data_br(h['alterado_em'])}   {servidor.reais_curto(h['limite_anterior'])} » "
                                    f"[b]{servidor.reais_curto(h['limite_novo'])}[/b]   ({MOTIVO.get(h['motivo'], h['motivo'])})"))

    def _depois(self, msg):
        def f(_r):
            aviso(msg)
            self.on_pre_enter()
            App.get_running_app().mostrar_novidades()
        return f

    def open_finance(self):
        def escolher(r):
            nomes = [i["nome"] for i in r["instituicoes"]]
            conectadas = ", ".join(c["instituicao"] for c in r["conexoes"] if c["status"] == "autorizado") or "nenhuma"
            abrir_formulario("Conectar Open Finance", [("banco", "Banco", "opcoes:" + ",".join(nomes), nomes[0])],
                             "Autorizar", lambda v: servidor.post(
                                 "/open-finance/conectar",
                                 {"instituicao_id": next(i["id"] for i in r["instituicoes"] if i["nome"] == v["banco"])},
                                 ao_receber=self._depois("Open Finance conectado! Sua renda extra entrou na análise."),
                                 ao_falhar=lambda m: aviso(m, erro=True)),
                             explicacao="Você autoriza a Vértis a ler seu histórico em outro banco por 12 meses. "
                                        "Quem tem pouco histórico aqui ganha limite mais rápido. "
                                        f"Já conectados: {conectadas}. (Simulado para a demonstração.)")
        servidor.get("/open-finance/instituicoes", ao_receber=escolher, ao_falhar=lambda m: aviso(m, erro=True))

    def emprestimo(self):
        def simular(v):
            def proposta(p):
                if p["status"] == "recusada":
                    aviso(p.get("motivo", "Não aprovado ainda"), erro=True)
                    return
                abrir_formulario("Sua proposta personalizada", [], "Contratar",
                                 lambda _v: servidor.post(f"/emprestimos/{p['id']}/contratar", {},
                                                          ao_receber=self._depois("Dinheiro na conta!"),
                                                          ao_falhar=lambda m: aviso(m, erro=True)),
                                 explicacao=(f"Valor aprovado: {servidor.reais(p['valor_aprovado'])}\n"
                                             f"{p['num_parcelas']}x de {servidor.reais(p['valor_parcela'])}\n"
                                             f"Juros: {float(p['taxa_juros_mensal']):.2f}% ao mês  •  "
                                             f"CET: {float(p['cet_anual']):.2f}% ao ano\n"
                                             "A taxa foi calculada pelo seu perfil de risco atual."))
            servidor.post("/emprestimos/simular", {"valor": numero(v["valor"]), "parcelas": int(numero(v["parcelas"], 6)),
                                                   "finalidade": v["finalidade"]},
                          ao_receber=proposta, ao_falhar=lambda m: aviso(m, erro=True))
        abrir_formulario("Simular empréstimo", [("valor", "Quanto você precisa?", "dinheiro", "1000"),
                                                ("parcelas", "Parcelas", "opcoes:3,6,10,12,18,24", "6"),
                                                ("finalidade", "Para quê?", "opcoes:Quitar dívida,Capital de giro,Estudos,Emergência", "Quitar dívida")],
                         "Simular", simular)
