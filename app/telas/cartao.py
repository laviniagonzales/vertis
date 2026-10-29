"""
TELA DO CARTÃO — cartão 3D, limite e fatura
==========================================
O cartão 3D (cg/cartao3d.py) pode ser girado com o dedo.
O limite NÃO é do cartão: vem de limites_credito (vale para todos os cartões).
"""
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import BooleanProperty, DictProperty, NumericProperty, StringProperty

import servidor
from telas.componentes import TelaVertis, aviso
from telas.formulario import abrir_formulario, numero

Builder.load_string("""
#:import rgba tema.rgba
#:import CORES tema.CORES
#:import servidor servidor

<TelaCartao>:
    BoxLayout:
        orientation: 'vertical'
        BoxLayout:
            size_hint_y: None
            height: dp(44)
            padding: dp(16), dp(8), dp(16), 0
            TextoTitulo:
                text: 'Meu cartão'
            TextoPequeno:
                text: 'arraste para girar'
                halign: 'right'
        Cartao3D:
            id: cartao
            size_hint_y: None
            height: dp(230)
        BoxLayout:
            size_hint_y: None
            height: dp(44)
            padding: dp(16), 0
            spacing: dp(10)
            BotaoContorno:
                text: 'Virar cartão'
                on_release: cartao.virar()
            BotaoContorno:
                text: root.texto_bloqueio
                on_release: root.alternar_bloqueio()
            BotaoContorno:
                text: 'Nova compra'
                on_release: root.nova_compra()
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: dp(16), dp(10)
                spacing: dp(12)
                Painel:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(130)
                    TextoPequeno:
                        text: 'Limite disponível'
                    Texto:
                        text: '[b]' + servidor.reais(servidor.campo(root.limite, 'limite_disponivel', padrao=0)) + '[/b]  de ' + servidor.reais(servidor.campo(root.limite, 'limite_total', padrao=0))
                        font_size: sp(18)
                    BarraProgresso:
                        valor: root.fracao_uso
                        cor: rgba(CORES['rosa'])
                    TextoPequeno:
                        text: 'Utilizado: ' + servidor.reais(servidor.campo(root.limite, 'limite_utilizado', padrao=0))
                    TextoPequeno:
                        text: '[color=#FFE29A]Próximo limite previsto: ' + servidor.reais(servidor.campo(root.limite, 'proximo_limite_previsto', padrao=0)) + '[/color]  (pague em dia!)'
                Painel:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(150)
                    TextoPequeno:
                        text: root.titulo_fatura
                    Texto:
                        text: '[b]' + root.valor_fatura + '[/b]'
                        font_size: sp(24)
                    TextoPequeno:
                        text: root.detalhe_fatura
                    BotaoVertis:
                        text: root.texto_pagar
                        disabled: not root.fatura_pagavel
                        opacity: 1 if root.fatura_pagavel else 0.4
                        cor: rgba(CORES['dourado'])
                        cor_texto: rgba('#1A0E3D')
                        on_release: root.pagar()
                TextoPequeno:
                    text: root.lancamentos
        BarraNavegacao:
            atual: 'cartao'
""")


class TelaCartao(TelaVertis):
    limite = DictProperty({})
    fracao_uso = NumericProperty(0)
    titulo_fatura = StringProperty("Fatura")
    valor_fatura = StringProperty("")
    detalhe_fatura = StringProperty("")
    texto_pagar = StringProperty("Pagar fatura")
    texto_bloqueio = StringProperty("Bloquear")
    lancamentos = StringProperty("")
    fatura_pagavel = BooleanProperty(False)
    _fatura_id = None
    _cartao_id = None

    def on_pre_enter(self, *_):
        self.carregar()

    def carregar(self):
        servidor.get("/cartoes", ao_receber=self._preencher, ao_falhar=lambda m: aviso(m, erro=True))
        servidor.get("/me/resumo", ao_receber=lambda r: self._dados_cartao(nivel=r["nivel"]["nome"]))

    def _dados_cartao(self, **extra):
        d = dict(self.ids.cartao.dados)
        d.update(extra)
        self.ids.cartao.dados = d

    def _preencher(self, r):
        self.limite = r["limite"]
        total = float(r["limite"]["limite_total"]) or 1
        self.fracao_uso = float(r["limite"]["limite_utilizado"]) / total
        virtual = next((c for c in r["cartoes"] if c["formato"] == "virtual"), r["cartoes"][0])
        self._cartao_id = virtual["id"]
        self.texto_bloqueio = "Desbloquear" if virtual["status"] == "bloqueado_temporario" else "Bloquear"
        self._dados_cartao(nome=virtual["nome_impresso"], final=virtual["final_cartao"], validade=virtual["validade"],
                           bandeira=virtual["bandeira"], limite=servidor.reais_curto(r["limite"]["limite_total"]))

        faturas = r["faturas"]
        pagar = next((f for f in faturas if f["status"] in ("fechada", "paga_parcial", "atrasada")), None)
        aberta = next((f for f in faturas if f["status"] == "aberta"), None)
        f = pagar or aberta
        self.fatura_pagavel = pagar is not None
        if not f:
            self.titulo_fatura, self.valor_fatura, self.detalhe_fatura = "Fatura", servidor.reais(0), "Nenhuma compra ainda."
            self.lancamentos = ""
            return
        self._fatura_id = f["id"]
        situacao = {"aberta": "Fatura aberta", "fechada": "Fatura fechada", "atrasada": "[color=#F87171]Fatura ATRASADA[/color]",
                    "paga_parcial": "Fatura paga parcialmente"}[f["status"]]
        self.titulo_fatura = f"{situacao} — {f['mes_referencia']}"
        self.valor_fatura = servidor.reais(float(f["valor_total"]) - float(f["valor_pago"]))
        self.detalhe_fatura = (f"Fecha em {servidor.data_br(f['data_fechamento'])}  •  "
                               f"Vence em {servidor.data_br(f['data_vencimento'])}")
        self.texto_pagar = "Pagar fatura (em dia = limite sobe!)" if pagar else "Aguardando fechamento"
        itens = [l for l in f["lancamentos"] if l["tipo"] != "pagamento"][-6:]
        self.lancamentos = "   Últimos lançamentos:\n" + "\n".join(
            f"   • {l['descricao']}: {servidor.reais(l['valor'])}" for l in itens) if itens else ""

    def pagar(self):
        if not self._fatura_id:
            return

        def pago(r):
            efeitos = r.get("efeitos") or {}
            ganhos = efeitos.get("recompensas") or {}
            aviso(f"Fatura paga! +{ganhos.get('xp', 0)} XP, +{servidor.milhar(ganhos.get('pontos', 0))} pontos, "
                  f"+{servidor.milhar(ganhos.get('milhas', 0))} milhas")
            self.carregar()
            App.get_running_app().mostrar_novidades()
        servidor.post(f"/faturas/{self._fatura_id}/pagar", {}, ao_receber=pago, ao_falhar=lambda m: aviso(m, erro=True))

    def alternar_bloqueio(self):
        if self._cartao_id:
            servidor.post(f"/cartoes/{self._cartao_id}/bloqueio", {},
                          ao_receber=lambda r: (aviso("Cartão " + ("bloqueado" if r["status"] != "ativo" else "desbloqueado")),
                                                self.carregar()),
                          ao_falhar=lambda m: aviso(m, erro=True))

    def nova_compra(self):
        def comprar(v):
            servidor.post("/cartoes/compra", {"valor": numero(v["valor"]), "estabelecimento": v["loja"],
                                              "parcelas": int(numero(v["parcelas"], 1)), "categoria": v["categoria"]},
                          ao_receber=lambda r: (aviso("Compra aprovada!" if r["status"] == "autorizada"
                                                      else f"Compra NEGADA: {r.get('motivo_negativa')}",
                                                      erro=r["status"] != "autorizada"), self.carregar()),
                          ao_falhar=lambda m: aviso(m, erro=True))
        abrir_formulario("Simular compra no cartão",
                         [("loja", "Estabelecimento", "texto", "Mercado Bom Preço"),
                          ("valor", "Valor (R$)", "numero", "89.90"),
                          ("parcelas", "Parcelas", "opcoes:1,2,3,4,5,6,10,12", "1"),
                          ("categoria", "Categoria", "opcoes:Alimentação,Transporte,Saúde,Lazer,Educação,Compras", "Alimentação")],
                         "Comprar", comprar, explicacao="Compra no crédito: usa o limite e entra na fatura.")
