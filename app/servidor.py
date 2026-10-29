"""
COMUNICAÇÃO COM A API
====================
O app nunca fala com o MySQL. Ele manda pedidos HTTP para a API e recebe
respostas em JSON (texto no formato de dicionário).

Usamos o UrlRequest do próprio Kivy porque ele é ASSÍNCRONO: o pedido vai
"em segundo plano" e o app continua respondendo (sem travar a tela).
Quando a resposta chega, ele chama a função que passamos (ao_receber).
"""
import json
import os

from kivy.network.urlrequest import UrlRequest
from kivy.storage.jsonstore import JsonStore

_estado = {"url": "http://127.0.0.1:8000", "token": None, "loja": None}


def iniciar(pasta_dados: str):
    """Carrega o endereço do servidor salvo no celular (se houver)."""
    _estado["loja"] = JsonStore(os.path.join(pasta_dados, "vertis_config.json"))
    if _estado["loja"].exists("servidor"):
        _estado["url"] = _estado["loja"].get("servidor")["url"]


def definir_url(url: str):
    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "http://" + url
    _estado["url"] = url
    if _estado["loja"] is not None:
        _estado["loja"].put("servidor", url=url)


def url_atual() -> str:
    return _estado["url"]


def definir_token(token: str | None):
    _estado["token"] = token


def _pedido(metodo, rota, dados, ao_receber, ao_falhar):
    cabecalhos = {"Content-Type": "application/json"}
    if _estado["token"]:
        cabecalhos["Authorization"] = f"Bearer {_estado['token']}"

    def sucesso(_req, resposta):
        if ao_receber:
            ao_receber(resposta)

    def erro_http(req, resposta):
        mensagem = resposta.get("detail") if isinstance(resposta, dict) else None
        if isinstance(mensagem, list):           # erro de validação do FastAPI
            mensagem = "Confira os dados: " + ", ".join(str(m.get("loc", [""])[-1]) for m in mensagem)
        if ao_falhar:
            ao_falhar(mensagem or f"Erro {req.resp_status}")

    def sem_conexao(_req, _erro):
        if ao_falhar:
            ao_falhar(f"Não consegui falar com o servidor ({_estado['url']}). A API está rodando?")

    UrlRequest(_estado["url"] + rota, method=metodo, req_headers=cabecalhos,
               req_body=json.dumps(dados) if dados is not None else None,
               on_success=sucesso, on_failure=erro_http, on_error=sem_conexao, timeout=60)


def get(rota, ao_receber=None, ao_falhar=None):
    _pedido("GET", rota, None, ao_receber, ao_falhar)


def post(rota, dados=None, ao_receber=None, ao_falhar=None):
    _pedido("POST", rota, dados if dados is not None else {}, ao_receber, ao_falhar)


# ---------------------------------------------------------------- formatação
def reais(valor) -> str:
    """1234.5 → 'R$ 1.234,50'"""
    texto = f"{float(valor or 0):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def reais_curto(valor) -> str:
    """1234.5 → 'R$ 1.234'"""
    texto = f"{float(valor or 0):,.0f}"
    return "R$ " + texto.replace(",", ".")


def milhar(n) -> str:
    return f"{int(n or 0):,}".replace(",", ".")


def data_br(texto_iso: str | None) -> str:
    if not texto_iso:
        return "-"
    data = str(texto_iso)[:10].split("-")
    return f"{data[2]}/{data[1]}/{data[0]}" if len(data) == 3 else str(texto_iso)


def campo(dicionario, *chaves, padrao=0):
    """Lê dicionario[ch1][ch2]... com valor padrão.
    Usado no KV no lugar de .get(): o KV só "percebe" que os dados mudaram
    quando o dicionário é passado como ARGUMENTO de uma função."""
    valor = dicionario
    for chave in chaves:
        if not isinstance(valor, dict) or chave not in valor or valor[chave] is None:
            return padrao
        valor = valor[chave]
    return valor
