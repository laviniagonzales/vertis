"""Janela (popup) de formulário reutilizável: título + campos + botões."""
from kivy.factory import Factory
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView

from telas.componentes import CampoDinheiro, Consentimento


def abrir_formulario(titulo, campos, texto_botao, ao_confirmar, explicacao=None):
    """campos = [(chave, dica, tipo, valor_inicial)]
    tipo: 'texto' | 'numero' | 'dinheiro' | 'opcoes:a,b,c' | 'sim_nao'"""
    janela = ModalView(size_hint=(0.9, None), background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0.08, 0.09, 0.11, 0.55))
    caixa = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(8), size_hint_y=None)
    caixa.bind(minimum_height=caixa.setter("height"))
    janela.height = dp(200)
    caixa.bind(height=lambda _w, h: setattr(janela, "height", h))
    with caixa.canvas.before:
        Color(1, 1, 1, 1)
        fundo = RoundedRectangle(radius=[dp(16)])
    caixa.bind(pos=lambda w, *_: setattr(fundo, "pos", w.pos), size=lambda w, *_: setattr(fundo, "size", w.size))

    caixa.add_widget(Factory.TextoTitulo(text=titulo))
    if explicacao:
        caixa.add_widget(Factory.TextoPequeno(text=explicacao))
    entradas = {}
    for chave, dica, tipo, inicial in campos:
        if tipo == "sim_nao":
            w = Consentimento(texto=dica, ativo=bool(inicial))
            caixa.add_widget(w)
            entradas[chave] = w
            continue
        caixa.add_widget(Factory.Rotulo(text=dica))
        if tipo.startswith("opcoes:"):
            w = Factory.Opcoes(text=str(inicial), values=tipo[7:].split(","))
        elif tipo == "dinheiro":
            w = CampoDinheiro(hint_text="R$ 0,00")
            w.definir(inicial)
        else:
            w = Factory.Campo(hint_text=dica, text=str(inicial or ""))
            if tipo == "numero":
                w.input_filter = "float"
                w.input_type = "number"
        caixa.add_widget(w)
        entradas[chave] = w

    def confirmar(*_):
        valores = {}
        for chave, w in entradas.items():
            if isinstance(w, Consentimento):
                valores[chave] = w.ativo
            elif isinstance(w, CampoDinheiro):
                valores[chave] = str(w.valor)
            else:
                valores[chave] = w.text
        janela.dismiss()
        ao_confirmar(valores)

    caixa.add_widget(Factory.Widget(size_hint_y=None, height=dp(6)))
    botoes = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
    cancelar = Factory.BotaoContorno(text="Cancelar", height=dp(48))
    cancelar.bind(on_release=lambda *_: janela.dismiss())
    ok = Factory.BotaoVertis(text=texto_botao)
    ok.bind(on_release=confirmar)
    botoes.add_widget(cancelar)
    botoes.add_widget(ok)
    caixa.add_widget(botoes)
    janela.add_widget(caixa)
    janela.open()
    return janela


def numero(texto, padrao=0.0) -> float:
    try:
        return float(str(texto).replace(",", "."))
    except ValueError:
        return padrao
