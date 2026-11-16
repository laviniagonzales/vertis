"""
TELA DE CADASTRO — módulo 1 do banco (clientes, endereços, consentimentos LGPD)
Como o público tem pouco histórico, a renda e a ocupação já entram aqui
para alimentar a análise de perfil.

Os campos de data, CPF, celular e renda têm MÁSCARA: as barras, pontos,
traços e o "R$" entram sozinhos enquanto o cliente digita (telas/componentes.py).
"""
from datetime import date

from kivy.app import App
from kivy.lang import Builder

import servidor
from telas.componentes import TelaVertis, aviso

# texto mostrado ao cliente → valor que a API espera
TIPOS_RENDA = {
    "Carteira assinada (CLT)": "formal",
    "Trabalho informal": "informal",
    "Autônomo / MEI": "autonomo",
    "Benefício (INSS, BPC...)": "beneficio",
    "Sem renda no momento": "sem_renda",
}

Builder.load_string("""
#:import rgba tema.rgba
#:import CORES tema.CORES

<SecaoForm@Painel>:
    orientation: 'vertical'
    size_hint_y: None
    height: self.minimum_height
    spacing: dp(6)

<TelaCadastro>:
    BoxLayout:
        orientation: 'vertical'
        BarraTopo:
            titulo: 'Abrir conta'
            voltar: True
            destino_voltar: 'login'
        ScrollView:
            do_scroll_x: False
            bar_width: dp(3)
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(12)
                padding: dp(16), dp(14), dp(16), dp(24)
                TextoPequeno:
                    text: 'Leva menos de 2 minutos. Seus dados ficam protegidos e você controla o que compartilha.'
                SecaoForm:
                    Texto:
                        text: '[b]Dados pessoais[/b]'
                        font_size: sp(16)
                    Rotulo:
                        text: 'Nome completo'
                    Campo:
                        id: nome
                        hint_text: 'Como está no seu documento'
                    Rotulo:
                        text: 'CPF'
                    CampoCPF:
                        id: cpf
                        hint_text: '000.000.000-00'
                    Rotulo:
                        text: 'Data de nascimento'
                    CampoData:
                        id: nascimento
                        hint_text: 'DD/MM/AAAA'
                    Rotulo:
                        text: 'E-mail'
                    Campo:
                        id: email
                        hint_text: 'seuemail@exemplo.com'
                        input_type: 'mail'
                    Rotulo:
                        text: 'Celular'
                    CampoTelefone:
                        id: telefone
                        hint_text: '(00) 00000-0000'
                SecaoForm:
                    Texto:
                        text: '[b]Renda[/b]'
                        font_size: sp(16)
                    TextoPequeno:
                        text: 'É com ela que calculamos seu primeiro limite.'
                    Rotulo:
                        text: 'Renda mensal'
                    CampoDinheiro:
                        id: renda
                        hint_text: 'R$ 0,00'
                    Rotulo:
                        text: 'Tipo de renda'
                    Opcoes:
                        id: tipo_renda
                        text: 'Trabalho informal'
                    Rotulo:
                        text: 'Profissão ou fonte de renda'
                    Campo:
                        id: ocupacao
                        hint_text: 'Ex.: entregador, manicure, vendedor'
                SecaoForm:
                    Texto:
                        text: '[b]Segurança[/b]'
                        font_size: sp(16)
                    Rotulo:
                        text: 'Crie uma senha'
                    Campo:
                        id: senha
                        hint_text: 'Mínimo de 6 caracteres'
                        password: True
                    Rotulo:
                        text: 'Confirme a senha'
                    Campo:
                        id: senha2
                        hint_text: 'Digite a senha novamente'
                        password: True
                SecaoForm:
                    Texto:
                        text: '[b]Privacidade (LGPD)[/b]'
                        font_size: sp(16)
                    TextoPequeno:
                        text: 'Você pode revogar essas autorizações quando quiser.'
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
                    text: 'Criar minha conta'
                    on_release: root.enviar()
""")


def validar_data(texto: str):
    """'14/03/1998' → date(1998, 3, 14), ou None se a data não existir."""
    try:
        dia, mes, ano = (int(p) for p in texto.split("/"))
        return date(ano, mes, dia)
    except ValueError:
        return None


class TelaCadastro(TelaVertis):
    def on_kv_post(self, *_):
        self.ids.tipo_renda.values = list(TIPOS_RENDA.keys())

    def enviar(self):
        i = self.ids
        if not i.nome.text.strip():
            aviso("Informe seu nome completo", erro=True)
            return
        if not i.cpf.completo:
            aviso("CPF incompleto: são 11 números", erro=True)
            return
        nascimento = validar_data(i.nascimento.text) if i.nascimento.completo else None
        if nascimento is None:
            aviso("Data de nascimento inválida", erro=True)
            return
        hoje = date.today()
        idade = hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
        if idade < 18 or idade > 120:
            aviso("É preciso ter 18 anos ou mais para abrir a conta", erro=True)
            return
        if len(i.senha.text) < 6:
            aviso("A senha precisa ter pelo menos 6 caracteres", erro=True)
            return
        if i.senha.text != i.senha2.text:
            aviso("As senhas não conferem", erro=True)
            return
        if not (i.c_credito.ativo and i.c_comport.ativo):
            aviso("As duas primeiras autorizações são obrigatórias", erro=True)
            return

        dados = {
            "nome_completo": i.nome.text.strip(), "cpf": i.cpf.digitos, "data_nascimento": nascimento.isoformat(),
            "email": i.email.text.strip(), "telefone": i.telefone.digitos,
            "renda_mensal_declarada": i.renda.valor, "ocupacao": i.ocupacao.text,
            "tipo_renda": TIPOS_RENDA.get(i.tipo_renda.text, "sem_renda"), "senha": i.senha.text,
            "consentimentos": {"analise_credito": i.c_credito.ativo, "uso_dados_comportamentais": i.c_comport.ativo,
                               "compartilhamento_parceiros": i.c_parceiros.ativo, "marketing": i.c_marketing.ativo},
        }

        def criado(r):
            aviso(f"Conta {r['conta']} aberta! Limite inicial: {servidor.reais(r['limite_inicial'])}")
            login = App.get_running_app().root.get_screen("login")
            login.ids.cpf.text = i.cpf.digitos
            login.entrar(i.cpf.digitos, i.senha.text)

        servidor.post("/auth/cadastro", dados, ao_receber=criado, ao_falhar=lambda m: aviso(m, erro=True))
