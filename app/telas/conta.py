"""
TELA DA CONTA DIGITAL — saldo, extrato, Pix e metas
==================================================
VISIBILIDADE / RECORTE no dia a dia: o extrato fica dentro de um
ScrollView. O Kivy usa um "stencil" (máscara) para RECORTAR tudo o que
passa da área visível — o mesmo princípio do recorte que vimos em aula.
"""
from kivy.app import App
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import BooleanProperty, DictProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout

import servidor
from telas.componentes import TelaVertis, aviso
from telas.formulario import abrir_formulario, numero

Builder.load_string("""
#:import rgba tema.rgba
#:import CORES tema.CORES
#:import servidor servidor

<LinhaExtrato>:
    size_hint_y: None
    height: dp(54)
    spacing: dp(10)
    padding: dp(4), dp(4)
    Widget:
        size_hint_x: None
        width: dp(10)
        canvas:
            Color:
                rgba: rgba(root.cor_categoria)
            Ellipse:
                pos: self.center_x - dp(5), self.center_y - dp(5)
                size: dp(10), dp(10)
    BoxLayout:
        orientation: 'vertical'
        Texto:
            text: root.descricao
            shorten: True
            font_size: sp(14)
        TextoPequeno:
            text: root.detalhe
            font_size: sp(11)
    Label:
        text: root.valor
        bold: True
        font_size: sp(14)
        color: rgba(CORES['verde']) if root.entrada else rgba(CORES['texto'])
        size_hint_x: None
        width: dp(104)
        text_size: self.size
        halign: 'right'
        valign: 'middle'

<TelaConta>:
    BoxLayout:
        orientation: 'vertical'
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: dp(260)
            padding: dp(16), dp(14), dp(16), dp(6)
            spacing: dp(10)
            TextoTitulo:
                text: 'Minha conta'
            Painel:
                orientation: 'vertical'
                size_hint_y: None
                height: dp(104)
                TextoPequeno:
                    text: 'Saldo disponível'
                Label:
                    text: servidor.reais(servidor.campo(root.dados, 'saldo', padrao=0))
                    font_size: sp(30)
                    bold: True
                    text_size: self.size
                    halign: 'left'
                    valign: 'middle'
                TextoPequeno:
                    text: 'Agência ' + servidor.campo(root.dados, 'agencia', padrao='') + '  •  Conta ' + servidor.campo(root.dados, 'numero', padrao='') + '  •  Pix: ' + root.chave
                    font_size: sp(11)
            GridLayout:
                cols: 2
                spacing: dp(10)
                size_hint_y: None
                height: dp(98)
                BotaoVertis:
                    text: 'Enviar Pix'
                    on_release: root.enviar_pix()
                BotaoVertis:
                    text: 'Receber (simular)'
                    cor: rgba('#4C3A99')
                    on_release: root.receber()
                BotaoVertis:
                    text: 'Minhas metas'
                    cor: rgba('#4C3A99')
                    on_release: root.metas()
                BotaoVertis:
                    text: 'Meu score'
                    cor: rgba('#4C3A99')
                    on_release: app.ir('score')
        TextoPequeno:
            text: '   Extrato'
            size_hint_y: None
            height: dp(22)
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: lista
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: dp(14), 0
        BarraNavegacao:
            atual: 'conta'
""")


class LinhaExtrato(BoxLayout):
    descricao = StringProperty("")
    detalhe = StringProperty("")
    valor = StringProperty("")
    entrada = BooleanProperty(False)
    cor_categoria = StringProperty("#94A3B8")


class TelaConta(TelaVertis):
    dados = DictProperty({})
    chave = StringProperty("")

    def on_pre_enter(self, *_):
        self.carregar()

    def carregar(self):
        servidor.get("/conta/extrato", ao_receber=self._preencher, ao_falhar=lambda m: aviso(m, erro=True))

    def _preencher(self, r):
        self.dados = r
        chaves = r.get("chaves_pix", [])
        self.chave = next((c["valor_chave"] for c in chaves if c["tipo_chave"] == "email"), "")
        lista = self.ids.lista
        lista.clear_widgets()
        if not r["transacoes"]:
            lista.add_widget(Factory.TextoPequeno(text="Nenhuma movimentação ainda."))
        for t in r["transacoes"]:
            entrada = t["direcao"] == "entrada"
            lista.add_widget(Factory.LinhaExtrato(
                descricao=t["descricao"] or t["tipo"], entrada=entrada,
                detalhe=f"{servidor.data_br(t['realizada_em'])}  •  {t['categoria'] or t['tipo'].replace('_', ' ')}",
                valor=("+ " if entrada else "- ") + servidor.reais(t["valor"]),
                cor_categoria=t["categoria_cor"] or "#94A3B8"))

    def _depois(self, msg):
        def f(_r):
            aviso(msg)
            self.carregar()
            App.get_running_app().mostrar_novidades()
        return f

    def enviar_pix(self):
        abrir_formulario("Enviar Pix", [("chave", "Chave Pix (CPF, e-mail...)", "texto", ""),
                                        ("valor", "Valor (R$)", "numero", ""),
                                        ("descricao", "Descrição (opcional)", "texto", "")], "Enviar",
                         lambda v: servidor.post("/pix/enviar", {"chave": v["chave"], "valor": numero(v["valor"]),
                                                                 "descricao": v["descricao"] or None},
                                                 ao_receber=self._depois("Pix enviado!"),
                                                 ao_falhar=lambda m: aviso(m, erro=True)),
                         explicacao="Se a chave for de outro cliente Vértis, o dinheiro cai na conta dele na hora.")

    def receber(self):
        abrir_formulario("Simular recebimento", [("valor", "Valor (R$)", "numero", "2500"),
                                                 ("de_nome", "Quem enviou", "texto", "Plataforma de Entregas"),
                                                 ("eh_salario", "É o meu salário", "sim_nao", True)], "Receber",
                         lambda v: servidor.post("/pix/simular-recebimento",
                                                 {"valor": numero(v["valor"]), "de_nome": v["de_nome"],
                                                  "eh_salario": v["eh_salario"]},
                                                 ao_receber=self._depois("Pix recebido!"),
                                                 ao_falhar=lambda m: aviso(m, erro=True)),
                         explicacao="Para a demonstração: simula um Pix chegando de outro banco. "
                                    "Salário recebido aqui conta como renda comprovada!")

    def metas(self):
        def mostrar(lista):
            if not lista:
                abrir_formulario("Nova meta", [("nome", "Nome da meta", "texto", "Reserva de emergência"),
                                               ("alvo", "Valor alvo (R$)", "numero", "1500")], "Criar",
                                 lambda v: servidor.post("/metas", {"nome": v["nome"], "valor_alvo": numero(v["alvo"])},
                                                         ao_receber=self._depois("Meta criada!"),
                                                         ao_falhar=lambda m: aviso(m, erro=True)))
                return
            m = next((x for x in lista if x["status"] == "ativa"), lista[-1])
            texto = (f"{m['nome']}: {servidor.reais(m['valor_atual'])} de {servidor.reais(m['valor_alvo'])}"
                     + ("  (concluída!)" if m["status"] == "concluida" else ""))
            if m["status"] != "ativa":
                aviso(texto)
                return
            abrir_formulario("Guardar dinheiro", [("valor", "Quanto guardar (R$)", "numero", "100")], "Guardar",
                             lambda v: servidor.post(f"/metas/{m['id']}/aportar", {"valor": numero(v["valor"])},
                                                     ao_receber=self._depois("Guardado na meta!"),
                                                     ao_falhar=lambda e: aviso(e, erro=True)),
                             explicacao=texto + "\nAo atingir a meta você ganha pontos e milhas.")
        servidor.get("/metas", ao_receber=mostrar, ao_falhar=lambda m: aviso(m, erro=True))
