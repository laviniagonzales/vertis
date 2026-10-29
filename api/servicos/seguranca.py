"""
SEGURANÇA: SENHAS E TOKENS
==========================
1) SENHA → HASH
   Nunca guardamos a senha. Guardamos o resultado do PBKDF2: uma função
   que "embaralha" a senha milhares de vezes junto com um SAL aleatório.
   Para conferir o login, embaralhamos a senha digitada do mesmo jeito e
   comparamos os resultados.

2) TOKEN DE ACESSO
   Depois do login, o app recebe um "crachá" (token) e o envia em toda
   requisição. O token tem o id do cliente + validade + uma ASSINATURA
   (HMAC). Se alguém alterar o token, a assinatura não bate e a API recusa.
"""
import base64
import hashlib
import hmac
import json
import os
import time

import config

_ITERACOES = 120_000


# ---------------------------------------------------------------- senhas
def gerar_hash_senha(senha: str) -> str:
    sal = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, _ITERACOES)
    return f"pbkdf2_sha256${_ITERACOES}${sal.hex()}${h.hex()}"


def conferir_senha(senha: str, senha_hash: str) -> bool:
    try:
        _, iteracoes, sal_hex, hash_hex = senha_hash.split("$")
        h = hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal_hex), int(iteracoes))
        return hmac.compare_digest(h.hex(), hash_hex)
    except ValueError:
        return False


# ---------------------------------------------------------------- tokens
def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).decode().rstrip("=")


def _de_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _assinar(conteudo: str) -> str:
    return _b64(hmac.new(config.CHAVE_TOKEN.encode(), conteudo.encode(), hashlib.sha256).digest())


def gerar_token(cliente_id: str) -> str:
    validade = int(time.time()) + config.HORAS_VALIDADE_TOKEN * 3600
    conteudo = _b64(json.dumps({"cid": cliente_id, "exp": validade}).encode())
    return f"{conteudo}.{_assinar(conteudo)}"


def ler_token(token: str) -> str | None:
    """Devolve o cliente_id se o token for válido; senão, None."""
    try:
        conteudo, assinatura = token.split(".")
        if not hmac.compare_digest(assinatura, _assinar(conteudo)):
            return None
        dados = json.loads(_de_b64(conteudo))
        if dados["exp"] < time.time():
            return None
        return dados["cid"]
    except (ValueError, KeyError):
        return None


# ---------------------------------------------------------------- CPF
def cpf_valido(cpf: str) -> bool:
    """Confere os 2 dígitos verificadores do CPF (algoritmo oficial)."""
    cpf = "".join(c for c in cpf if c.isdigit())
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for posicao in (9, 10):
        soma = sum(int(cpf[i]) * (posicao + 1 - i) for i in range(posicao))
        digito = (soma * 10) % 11 % 10
        if digito != int(cpf[posicao]):
            return False
    return True


def gerar_cpf_valido(semente: int) -> str:
    """Gera um CPF fictício (porém válido) para os clientes de demonstração."""
    base = [int(c) for c in f"{semente:09d}"[-9:]]
    for posicao in (9, 10):
        soma = sum(base[i] * (posicao + 1 - i) for i in range(posicao))
        base.append((soma * 10) % 11 % 10)
    return "".join(map(str, base))
