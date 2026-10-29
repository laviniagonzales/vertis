"""
TELA DE CADASTRO — módulo 1 do banco (clientes, endereços, consentimentos LGPD)
Como o público tem pouco histórico, a renda e a ocupação já entram aqui
para alimentar a análise de perfil.
"""
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout

import servidor
from telas.componentes import TelaVertis, aviso

Builder.load_string("""
#:import rgba tema.rgba
#:import CORES tema.CORES

<Consentimento>:
    size_hint_y: None
    height: dp(44)
    spacing: dp(8)
    CheckBox:
        size_hint_x: None
        width: dp(32)
        active: root.ativo
        on_active: root.ativo = self.active
        color: rgba(CORES['dourado'])
    TextoPequeno:
        text: root.texto
        color: rgba(CORES['texto'])
        pos_hint: {'center_y': .5}

<TelaCadastro>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(18), dp(16), dp(18), dp(12)
        spacing: dp(8)
        BoxLayout:
            size_hint_y: None
            height: dp(40)
            BotaoContorno:
                text: '< Voltar'
                size_hint_x: None
                width: dp(90)
                height: dp(34)
                on_release: app.ir('login', 'right')
            TextoTitulo:
                text: '  Abrir conta'
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
                padding: 0, dp(4), 0, dp(20)
                TextoPequeno:
                    text: 'Seus dados'
                Campo:
                    id: nome
                    hint_text: 'Nome completo'
                Campo:
                    id: cpf
                    hint_text: 'CPF (só números)'
                    input_filter: 'int'
                Campo:
                    id: nascimento
                    hint_text: 'Data de nascimento (DD/MM/AAAA)'
                Campo:
                    id: email
                    hint_text: 'E-mail'
                Campo:
                    id: telefone
                    hint_text: 'Celular com DDD'
                    input_filter: 'int'
                TextoPequeno:
                    text: 'Sua renda (é ela que define seu primeiro limite)'
                Campo:
                    id: renda
                    hint_text: 'Renda mensal (R$)'
                    input_filter: 'float'
                Campo:
                    id: ocupacao
                    hint_text: 'Profissão / fonte de renda'
                Spinner:
                    id: tipo_renda
                    text: 'informal'
                    values: ['formal', 'informal', 'autonomo', 'beneficio', 'sem_renda']
                    size_hint_y: None
                    height: dp(44)
                    background_normal: ''
                    background_color: rgba('#1C1240')
                Campo:
                    id: senha
                    hint_text: 'Crie uma senha (mín. 6 caracteres)'
                    password: True
                TextoPequeno:
                    text: 'Consentimentos (LGPD) — você pode revogar quando quiser'
                Consentimento:
                    id: c_credito
                    texto: 'Autorizo a análise de crédito (obrigatório)'
                    ativo: True
                Consentimento:
                    id: c_comport
                    texto: 'Autorizo o uso dos meus dados de comportamento para o crédito progressivo (obrigatório)'
                    ativo: True
                Consentimento:
                    id: c_parceiros
                    texto: 'Compartilhar com parceiros (salas VIP, companhias aéreas)'
                Consentimento:
                    id: c_marketing
                    texto: 'Receber ofertas e novidades'
                BotaoVertis:
                    text: 'Criar conta'
                    on_release: root.enviar()
""")


class Consentimento(BoxLayout):
    texto = StringProperty("")
    ativo = BooleanProperty(False)


class TelaCadastro(TelaVertis):
    def enviar(self):
        i = self.ids
        try:
            dia, mes, ano = i.nascimento.text.strip().split("/")
            nascimento = f"{int(ano):04d}-{int(mes):02d}-{int(dia):02d}"
        except ValueError:
            aviso("Data de nascimento no formato DD/MM/AAAA", erro=True)
            return
        dados = {
            "nome_completo": i.nome.text, "cpf": i.cpf.text, "data_nascimento": nascimento,
            "email": i.email.text, "telefone": i.telefone.text,
            "renda_mensal_declarada": float(i.renda.text or 0), "ocupacao": i.ocupacao.text,
            "tipo_renda": i.tipo_renda.text, "senha": i.senha.text,
            "consentimentos": {"analise_credito": i.c_credito.ativo, "uso_dados_comportamentais": i.c_comport.ativo,
                               "compartilhamento_parceiros": i.c_parceiros.ativo, "marketing": i.c_marketing.ativo},
        }

        def criado(r):
            aviso(f"Conta {r['conta']} aberta! Limite inicial: {servidor.reais(r['limite_inicial'])}")
            login = App.get_running_app().root.get_screen("login")
            login.ids.cpf.text = i.cpf.text
            login.entrar(i.cpf.text, i.senha.text)

        servidor.post("/auth/cadastro", dados, ao_receber=criado, ao_falhar=lambda m: aviso(m, erro=True))
