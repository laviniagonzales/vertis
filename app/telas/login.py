"""
TELAS DE LOGIN E CADASTRO
========================
Entrada de dados do fluxo: o cliente se cadastra (com os consentimentos
da LGPD) ou entra com CPF e senha. O botão "Cliente de demonstração"
cria o Gabriel na hora — ideal para a apresentação.
"""
import platform
import uuid

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import BooleanProperty

import servidor
from telas.componentes import TelaVertis, aviso

Builder.load_string("""
#:import rgba tema.rgba
#:import CORES tema.CORES

<LogoVertis@BoxLayout>:
    size_hint: None, None
    size: dp(220), dp(64)
    spacing: dp(10)
    Widget:
        size_hint_x: None
        width: dp(44)
        canvas:
            Color:
                rgba: rgba(CORES['dourado'])
            RoundedRectangle:
                pos: self.x, self.y + dp(10)
                size: dp(10), dp(16)
                radius: [dp(3)]
            RoundedRectangle:
                pos: self.x + dp(14), self.y + dp(10)
                size: dp(10), dp(26)
                radius: [dp(3)]
            RoundedRectangle:
                pos: self.x + dp(28), self.y + dp(10)
                size: dp(10), dp(38)
                radius: [dp(3)]
    Label:
        text: '[b]VÉRTIS[/b]'
        markup: True
        font_size: sp(36)
        color: 1, 1, 1, 1
        halign: 'left'
        text_size: self.size
        valign: 'middle'

<TelaLogin>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(26), dp(40), dp(26), dp(24)
        spacing: dp(12)
        Widget:
            size_hint_y: 0.25
        AnchorLayout:
            size_hint_y: None
            height: dp(70)
            LogoVertis:
        TextoPequeno:
            text: 'Crescimento vertical: crédito que cresce com você.'
            halign: 'center'
        Widget:
            size_hint_y: None
            height: dp(16)
        Campo:
            id: cpf
            hint_text: 'CPF (só números)'
            input_filter: 'int'
        Campo:
            id: senha
            hint_text: 'Senha'
            password: True
            on_text_validate: root.entrar()
        BotaoVertis:
            text: 'Entrar'
            on_release: root.entrar()
        BotaoContorno:
            text: 'Criar minha conta'
            on_release: app.ir('cadastro', 'left')
        BotaoContorno:
            text: 'Cliente de demonstração (Gabriel)'
            on_release: root.entrar_demo()
        Widget:
        BoxLayout:
            size_hint_y: None
            height: dp(40) if root.mostrar_servidor else dp(24)
            spacing: dp(6)
            TextoPequeno:
                text: 'Servidor:'
                size_hint_x: None
                width: dp(58)
                opacity: 1 if root.mostrar_servidor else 0
            Campo:
                id: url
                height: dp(36)
                font_size: sp(12)
                opacity: 1 if root.mostrar_servidor else 0
                disabled: not root.mostrar_servidor
                on_text_validate: root.salvar_servidor()
            Button:
                text: 'ok' if root.mostrar_servidor else 'servidor'
                size_hint_x: None
                width: dp(70)
                font_size: sp(11)
                background_normal: ''
                background_color: 0, 0, 0, 0
                color: rgba(CORES['texto2'])
                on_release: root.salvar_servidor() if root.mostrar_servidor else setattr(root, 'mostrar_servidor', True)
""")


def info_dispositivo():
    """Identifica o aparelho (vai para a tabela dispositivos)."""
    app = App.get_running_app()
    if not hasattr(app, "_id_dispositivo"):
        app._id_dispositivo = str(uuid.uuid5(uuid.NAMESPACE_DNS, platform.node() or "vertis"))
    from kivy.utils import platform as plataforma
    return {"dispositivo_id": app._id_dispositivo, "dispositivo_modelo": platform.node()[:100] or "desconhecido",
            "dispositivo_sistema": plataforma}


class TelaLogin(TelaVertis):
    mostrar_servidor = BooleanProperty(False)

    def on_pre_enter(self, *_):
        self.ids.url.text = servidor.url_atual()

    def salvar_servidor(self):
        servidor.definir_url(self.ids.url.text)
        self.mostrar_servidor = False
        aviso(f"Servidor: {servidor.url_atual()}")

    def entrar(self, cpf=None, senha=None):
        cpf = cpf or self.ids.cpf.text
        senha = senha or self.ids.senha.text
        if not cpf or not senha:
            aviso("Informe CPF e senha", erro=True)
            return
        servidor.post("/auth/login", {"cpf": cpf, "senha": senha, **info_dispositivo()},
                      ao_receber=self._logado, ao_falhar=lambda m: aviso(m, erro=True))

    def _logado(self, resposta):
        servidor.definir_token(resposta["token"])
        self.ids.senha.text = ""
        App.get_running_app().ir("inicio", "left")

    def entrar_demo(self):
        def criado(r):
            aviso(f"Cliente criado! CPF {r['cpf']} • senha {r['senha']}")
            self.ids.cpf.text = r["cpf"]
            self.entrar(r["cpf"], r["senha"])
        servidor.post("/demo/cliente", {}, ao_receber=criado, ao_falhar=lambda m: aviso(m, erro=True))
