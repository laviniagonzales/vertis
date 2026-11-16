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
    size: dp(200), dp(56)
    spacing: dp(10)
    Widget:
        size_hint_x: None
        width: dp(40)
        canvas:
            Color:
                rgba: rgba(CORES['amarelo'])
            RoundedRectangle:
                pos: self.x, self.y + dp(8)
                size: dp(9), dp(14)
                radius: [dp(2)]
            RoundedRectangle:
                pos: self.x + dp(13), self.y + dp(8)
                size: dp(9), dp(24)
                radius: [dp(2)]
            RoundedRectangle:
                pos: self.x + dp(26), self.y + dp(8)
                size: dp(9), dp(36)
                radius: [dp(2)]
    Label:
        text: '[b]VÉRTIS[/b]'
        markup: True
        font_size: sp(32)
        color: rgba(CORES['texto'])
        halign: 'left'
        text_size: self.size
        valign: 'middle'

<TelaLogin>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20), dp(24), dp(20), dp(12)
        spacing: dp(12)
        Widget:
            size_hint_y: 0.18
        AnchorLayout:
            size_hint_y: None
            height: dp(60)
            LogoVertis:
        TextoPequeno:
            text: 'Crédito que cresce com você.'
            halign: 'center'
            font_size: sp(13)
        Widget:
            size_hint_y: None
            height: dp(8)
        Painel:
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: dp(18)
            spacing: dp(8)
            Texto:
                text: '[b]Acesse sua conta[/b]'
                font_size: sp(17)
            Widget:
                size_hint_y: None
                height: dp(2)
            Rotulo:
                text: 'CPF'
            CampoCPF:
                id: cpf
                hint_text: '000.000.000-00'
            Rotulo:
                text: 'Senha'
            Campo:
                id: senha
                hint_text: 'Digite sua senha'
                password: True
                on_text_validate: root.entrar()
            Widget:
                size_hint_y: None
                height: dp(6)
            BotaoVertis:
                text: 'Entrar'
                on_release: root.entrar()
        BotaoContorno:
            text: 'Abrir minha conta'
            on_release: app.ir('cadastro', 'left')
        BotaoLink:
            text: 'Entrar com cliente de demonstração'
            on_release: root.entrar_demo()
        Widget:
        BoxLayout:
            size_hint_y: None
            height: dp(22)
            spacing: dp(6)
            Widget:
            Icone:
                icone: 'escudo'
                size_hint_x: None
                width: dp(16)
                cor: rgba(CORES['texto2'])
            Label:
                text: 'Ambiente seguro • dados protegidos pela LGPD'
                font_size: sp(11)
                color: rgba(CORES['texto2'])
                size_hint_x: None
                width: self.texture_size[0]
            Widget:
        BoxLayout:
            size_hint_y: None
            height: dp(40) if root.mostrar_servidor else dp(26)
            spacing: dp(6)
            TextoPequeno:
                text: 'Servidor:'
                size_hint_x: None
                width: dp(58)
                opacity: 1 if root.mostrar_servidor else 0
            Campo:
                id: url
                height: dp(38)
                padding: dp(10), dp(10)
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
                background_down: ''
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
        cpf = "".join(c for c in (cpf or self.ids.cpf.text) if c.isdigit())
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
