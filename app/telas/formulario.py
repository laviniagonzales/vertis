"""Janela (popup) de formulário reutilizável: título + campos + botão."""
from kivy.factory import Factory
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView

from tema import CORES, rgba


def abrir_formulario(titulo, campos, texto_botao, ao_confirmar, explicacao=None):
    """campos = [(chave, dica, tipo, valor_inicial)]  tipo: 'texto' | 'numero' | 'opcoes:a,b,c' | 'sim_nao'"""
    janela = ModalView(size_hint=(0.9, None), background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0.03, 0.01, 0.08, 0.75))
    caixa = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(10), size_hint_y=None)
    caixa.bind(minimum_height=caixa.setter("height"))
    with caixa.canvas.before:
        Color(*rgba("#22164A"))
        fundo = RoundedRectangle(radius=[dp(20)])
    caixa.bind(pos=lambda w, *_: setattr(fundo, "pos", w.pos), size=lambda w, *_: setattr(fundo, "size", w.size))

    caixa.add_widget(Factory.TextoTitulo(text=titulo))
    if explicacao:
        caixa.add_widget(Factory.TextoPequeno(text=explicacao))
    entradas = {}
    for chave, dica, tipo, inicial in campos:
        if tipo.startswith("opcoes:"):
            w = Factory.Spinner(text=str(inicial), values=tipo[7:].split(","), size_hint_y=None, height=dp(44),
                                background_normal="", background_color=rgba("#1C1240"))
            caixa.add_widget(Factory.TextoPequeno(text=dica))
        elif tipo == "sim_nao":
            linha = BoxLayout(size_hint_y=None, height=dp(40))
            w = Factory.CheckBox(active=bool(inicial), size_hint_x=None, width=dp(36), color=rgba(CORES["dourado"]))
            linha.add_widget(w)
            linha.add_widget(Factory.Texto(text=dica))
            caixa.add_widget(linha)
            entradas[chave] = w
            continue
        else:
            w = Factory.Campo(hint_text=dica, text=str(inicial or ""))
            if tipo == "numero":
                w.input_filter = "float"
        caixa.add_widget(w)
        entradas[chave] = w

    def confirmar(*_):
        valores = {}
        for chave, w in entradas.items():
            valores[chave] = w.active if hasattr(w, "active") else w.text
        janela.dismiss()
        ao_confirmar(valores)

    botoes = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
    cancelar = Factory.BotaoContorno(text="Cancelar", height=dp(46))
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
