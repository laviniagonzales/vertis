"""
APP VÉRTIS (Kivy) — ponto de partida
===================================
Como rodar no computador:   python main.py
(o app abre numa janela no formato de celular)

Para gerar o APK Android: veja o GUIA, seção "Gerar o APK".

Organização:
  main.py        → cria o app e as telas, navegação entre elas
  servidor.py    → conversa com a API (HTTP/JSON)
  tema.py        → cores
  cg/            → COMPUTAÇÃO GRÁFICA (conteúdo da disciplina)
  telas/         → uma tela por arquivo
"""
from kivy.utils import platform

if platform not in ("android", "ios"):
    # No computador, a janela imita a tela de um celular
    from kivy.config import Config
    Config.set("graphics", "width", "400")
    Config.set("graphics", "height", "820")
    Config.set("graphics", "resizable", "1")
    Config.set("input", "mouse", "mouse,multitouch_on_demand")   # sem bolinhas vermelhas ao clicar

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, SlideTransition

import servidor
from tema import rgba

# importar os widgets gráficos REGISTRA as classes para usarmos no KV
import cg.widgets      # noqa: F401
import cg.cartao3d     # noqa: F401
from telas.componentes import Celebracao, aviso
from telas.login import TelaLogin
from telas.cadastro import TelaCadastro
from telas.inicio import TelaInicio
from telas.conta import TelaConta
from telas.cartao import TelaCartao
from telas.conquistas import TelaConquistas
from telas.score import TelaScore
from telas.lab import TelaLab

ORDEM_ABAS = ["inicio", "conta", "cartao", "conquistas", "lab"]


class VertisApp(App):
    title = "Vértis"
    tela_anterior = None

    def build(self):
        Window.clearcolor = rgba("#0F0824")
        servidor.iniciar(self.user_data_dir)
        self.gerenciador = ScreenManager(transition=SlideTransition(duration=0.25))
        for tela in (TelaLogin(name="login"), TelaCadastro(name="cadastro"), TelaInicio(name="inicio"),
                     TelaConta(name="conta"), TelaCartao(name="cartao"), TelaConquistas(name="conquistas"),
                     TelaScore(name="score"), TelaLab(name="lab")):
            self.gerenciador.add_widget(tela)
        return self.gerenciador

    def ir(self, nome, direcao=None):
        atual = self.gerenciador.current
        if nome == atual:
            return
        if direcao is None:   # desliza para o lado certo, conforme a ordem das abas
            a = ORDEM_ABAS.index(atual) if atual in ORDEM_ABAS else -1
            b = ORDEM_ABAS.index(nome) if nome in ORDEM_ABAS else 99
            direcao = "left" if b > a else "right"
        self.tela_anterior = atual
        self.gerenciador.transition.direction = direcao
        self.gerenciador.current = nome

    def sair(self):
        servidor.definir_token(None)
        self.ir("login", "right")

    def mostrar_novidades(self):
        """Busca notificações novas e comemora as importantes (conquista, nível, limite)."""
        def recebidas(lista):
            importantes = [n for n in reversed(lista) if n["tipo"] in ("conquista", "nivel", "limite")]
            servidor.post("/notificacoes/marcar-lidas", {})
            if importantes:
                # no máximo 6 celebrações seguidas (prioridade: nível > conquista > limite)
                ordem = {"nivel": 0, "conquista": 1, "limite": 2}
                importantes = sorted(importantes, key=lambda n: ordem[n["tipo"]])[:6]
                Celebracao(importantes, ao_fechar=self._recarregar_tela).open()
        servidor.get("/notificacoes?nao_lidas=true", ao_receber=recebidas)

    def _recarregar_tela(self):
        tela = self.gerenciador.current_screen
        if hasattr(tela, "on_pre_enter"):
            tela.on_pre_enter()


if __name__ == "__main__":
    VertisApp().run()
