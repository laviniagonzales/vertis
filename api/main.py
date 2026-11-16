"""
API VÉRTIS  —  o "atendente" entre o app e o banco de dados
==========================================================
    📱 App (Kivy)  ──HTTP/JSON──▶  🔌 esta API (FastAPI)  ──SQL──▶  🗄️ MySQL

Por que o app não fala direto com o MySQL? Porque a senha do banco
ficaria dentro do app, e qualquer pessoa poderia extraí-la. A API
guarda essa senha, confere quem está pedindo (token) e aplica as regras.

Como rodar:      uvicorn main:app --host 0.0.0.0 --port 8000 --reload
Documentação:    abra http://localhost:8000/docs no navegador
                 (o FastAPI gera uma página para testar cada rota!)
"""
from datetime import date
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import relogio
from db import conexao, consultar
from servicos import (cartao, clientes, conta, credito, emprestimo, gamificacao, metas,
                      notificacoes, open_finance, seguranca, simulacao)

app = FastAPI(title="API Vértis", version="1.0",
              description="Crédito progressivo + gamificação para quem tem pouco histórico financeiro.")


# ============================================================ tratamento de erros
@app.exception_handler(ValueError)
async def erro_regra(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(PermissionError)
async def erro_acesso(_: Request, exc: PermissionError):
    return JSONResponse(status_code=401, content={"detail": str(exc)})


# ============================================================ autenticação
def cliente_logado(authorization: str = Header(default="")) -> str:
    """Toda rota protegida recebe o id do cliente a partir do token."""
    token = authorization.removeprefix("Bearer ").strip()
    cliente_id = seguranca.ler_token(token)
    if not cliente_id:
        raise HTTPException(401, "Faça login novamente")
    return cliente_id


# ============================================================ modelos de entrada
class Endereco(BaseModel):
    cep: str
    logradouro: str
    numero: str
    complemento: str | None = None
    bairro: str
    cidade: str
    uf: str


class Cadastro(BaseModel):
    nome_completo: str
    nome_social: str | None = None
    cpf: str
    data_nascimento: date
    email: str
    telefone: str
    renda_mensal_declarada: float | None = None
    ocupacao: str | None = None
    tipo_renda: Literal["formal", "informal", "autonomo", "beneficio", "sem_renda"] = "sem_renda"
    senha: str
    consentimentos: dict[str, bool] = {}
    endereco: Endereco | None = None


class Login(BaseModel):
    cpf: str
    senha: str
    dispositivo_id: str | None = None
    dispositivo_modelo: str | None = None
    dispositivo_sistema: str | None = None


class PixEnvio(BaseModel):
    chave: str
    valor: float = Field(gt=0)
    descricao: str | None = None


class PixRecebimento(BaseModel):
    valor: float = Field(gt=0)
    de_nome: str = "Cliente Externo"
    eh_salario: bool = False


class ContaConsumo(BaseModel):
    beneficiario: str = "Energia elétrica"
    valor: float = Field(gt=0)
    vencimento: date | None = None


class Compra(BaseModel):
    valor: float = Field(gt=0)
    estabelecimento: str
    parcelas: int = Field(default=1, ge=1, le=12)
    categoria: str = "Compras"
    funcao: Literal["credito", "debito"] = "credito"


class Pagamento(BaseModel):
    valor: float | None = None


class SimulacaoEmprestimo(BaseModel):
    valor: float = Field(gt=0)
    parcelas: int = Field(ge=1, le=24)
    finalidade: str | None = None


class Resgate(BaseModel):
    tipo: Literal["cashback", "transferencia_milhas"]
    quantidade: int = Field(gt=0)
    parceiro_id: str | None = None


class NovaMeta(BaseModel):
    nome: str
    valor_alvo: float = Field(gt=0)
    data_alvo: date | None = None


class Aporte(BaseModel):
    valor: float = Field(gt=0)


class Conexao(BaseModel):
    instituicao_id: str


class DemoMes(BaseModel):
    cliente_id: str
    comportamento: Literal["em_dia", "atrasa"] = "em_dia"


# ============================================================ rotas
@app.get("/", tags=["Sistema"])
def status():
    with conexao() as con:
        n = consultar(con, "SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema = DATABASE()")[0]["n"]
    return {"api": "Vértis", "ok": True, "tabelas_no_banco": n, "data_simulada": relogio.agora()}


# ---------------- Clientes e acesso
@app.post("/auth/cadastro", tags=["Clientes"])
def cadastrar(dados: Cadastro):
    with conexao() as con:
        try:
            return clientes.cadastrar(con, dados.model_dump())
        except clientes.ErroCadastro as e:
            raise HTTPException(400, str(e))


@app.post("/auth/login", tags=["Clientes"])
def login(dados: Login, request: Request):
    disp = None
    if dados.dispositivo_id:
        disp = {"identificador": dados.dispositivo_id, "modelo": dados.dispositivo_modelo,
                "sistema": dados.dispositivo_sistema}
    with conexao() as con:
        return clientes.login(con, dados.cpf, dados.senha, disp, request.client.host if request.client else None)


@app.get("/me/resumo", tags=["Tela de evolução"])
def resumo(cid: str = Depends(cliente_logado)):
    with conexao() as con:
        cartao.processar_ciclo(con, cid)      # rotina: fecha faturas / marca atrasos
        clientes.registrar_acesso(con, cid)   # evento acesso_app (1x por dia)
        return clientes.resumo(con, cid)


# ---------------- Conta digital
@app.get("/conta/extrato", tags=["Conta"])
def extrato(limite: int = 40, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        c = conta.conta_do_cliente(con, cid)
        return {"saldo": c["saldo_disponivel"], "agencia": c["agencia"],
                "numero": f"{c['numero_conta']}-{c['digito']}", "chaves_pix": conta.chaves(con, cid),
                "transacoes": conta.extrato(con, cid, limite)}


@app.post("/pix/enviar", tags=["Conta"])
def pix_enviar(dados: PixEnvio, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        try:
            return conta.pix_enviar(con, cid, dados.chave, dados.valor, dados.descricao)
        except conta.SaldoInsuficiente as e:
            raise HTTPException(400, str(e))


@app.post("/contas/pagar", tags=["Conta"])
def pagar_conta(dados: ContaConsumo, cid: str = Depends(cliente_logado)):
    """Paga uma conta de consumo (luz, água, celular). Paga em dia, ela ajuda o score."""
    with conexao() as con:
        try:
            return conta.pagar_conta(con, cid, dados.beneficiario, dados.valor, dados.vencimento)
        except conta.SaldoInsuficiente as e:
            raise HTTPException(400, str(e))


@app.post("/pix/simular-recebimento", tags=["Conta"])
def pix_receber(dados: PixRecebimento, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return conta.receber(con, cid, dados.valor, dados.de_nome, eh_salario=dados.eh_salario)


# ---------------- Cartões
@app.get("/cartoes", tags=["Cartões"])
def meus_cartoes(cid: str = Depends(cliente_logado)):
    with conexao() as con:
        cartao.processar_ciclo(con, cid)
        lim = consultar(con, "SELECT * FROM limites_credito WHERE cliente_id=%s", (cid,))[0]
        return {"cartoes": cartao.cartoes(con, cid), "limite": lim, "faturas": cartao.faturas(con, cid)}


@app.post("/cartoes/compra", tags=["Cartões"])
def comprar(dados: Compra, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return cartao.comprar(con, cid, dados.valor, dados.estabelecimento, dados.parcelas,
                              dados.categoria, dados.funcao)


@app.post("/cartoes/{cartao_id}/bloqueio", tags=["Cartões"])
def bloquear(cartao_id: str, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return {"status": cartao.alternar_bloqueio(con, cid, cartao_id)}


@app.post("/faturas/{fatura_id}/pagar", tags=["Cartões"])
def pagar_fatura(fatura_id: str, dados: Pagamento, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        try:
            return cartao.pagar_fatura(con, cid, fatura_id, dados.valor)
        except conta.SaldoInsuficiente as e:
            raise HTTPException(400, str(e))


# ---------------- Crédito
@app.get("/credito/score", tags=["Crédito"])
def score(cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return {"atual": credito.ultimo_score(con, cid),
                "perfil": consultar(con, "SELECT * FROM perfil_financeiro WHERE cliente_id=%s", (cid,))[0],
                "historico_score": consultar(con, """SELECT score_interno, calculado_em FROM scores_credito
                                                      WHERE cliente_id=%s ORDER BY calculado_em""", (cid,)),
                "historico_limite": consultar(con, """SELECT limite_anterior, limite_novo, motivo, alterado_em
                                                       FROM historico_limite WHERE cliente_id=%s
                                                       ORDER BY alterado_em""", (cid,))}


@app.post("/emprestimos/simular", tags=["Crédito"])
def simular_emprestimo(dados: SimulacaoEmprestimo, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return emprestimo.simular(con, cid, dados.valor, dados.parcelas, dados.finalidade)


@app.post("/emprestimos/{proposta_id}/contratar", tags=["Crédito"])
def contratar(proposta_id: str, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return emprestimo.contratar(con, cid, proposta_id)


@app.get("/emprestimos", tags=["Crédito"])
def emprestimos(cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return emprestimo.contratos(con, cid)


@app.post("/emprestimos/parcelas/{parcela_id}/pagar", tags=["Crédito"])
def pagar_parcela(parcela_id: str, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return emprestimo.pagar_parcela(con, cid, parcela_id)


# ---------------- Open Finance
@app.get("/open-finance/instituicoes", tags=["Open Finance"])
def instituicoes(cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return {"instituicoes": open_finance.instituicoes(con), "conexoes": open_finance.conexoes(con, cid)}


@app.post("/open-finance/conectar", tags=["Open Finance"])
def conectar(dados: Conexao, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return open_finance.conectar(con, cid, dados.instituicao_id)


# ---------------- Gamificação
@app.get("/gamificacao/conquistas", tags=["Gamificação"])
def conquistas(cid: str = Depends(cliente_logado)):
    with conexao() as con:
        lista = consultar(con, """
            SELECT c.codigo, c.nome, c.descricao, c.categoria, c.criterio_quantidade, c.pontos_recompensa,
                   cc.progresso_atual, cc.status, cc.conquistada_em, b.nome AS beneficio
              FROM conquistas c JOIN conquistas_cliente cc ON cc.conquista_id = c.id AND cc.cliente_id = %s
              LEFT JOIN beneficios b ON b.id = c.beneficio_id
             ORDER BY cc.status = 'conquistada' DESC, cc.conquistada_em, c.criterio_quantidade""", (cid,))
        niveis = consultar(con, "SELECT ordem, nome, xp_minimo, multiplicador_pontos, cor_hex FROM niveis ORDER BY ordem")
        return {"conquistas": lista, "niveis": niveis}


@app.get("/gamificacao/extrato", tags=["Gamificação"])
def extrato_recompensas(cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return consultar(con, """SELECT moeda, tipo, quantidade, saldo_apos, descricao, ocorrido_em
                                   FROM movimentacoes_recompensa WHERE cliente_id=%s
                                  ORDER BY ocorrido_em DESC, criado_em DESC LIMIT 50""", (cid,))


@app.post("/gamificacao/resgatar", tags=["Gamificação"])
def resgatar(dados: Resgate, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return gamificacao.resgatar(con, cid, dados.tipo, dados.quantidade, dados.parceiro_id)


# ---------------- Gestão financeira
@app.get("/metas", tags=["Gestão financeira"])
def listar_metas(cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return metas.listar(con, cid)


@app.post("/metas", tags=["Gestão financeira"])
def criar_meta(dados: NovaMeta, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return {"id": metas.criar(con, cid, dados.nome, dados.valor_alvo, dados.data_alvo)}


@app.post("/metas/{meta_id}/aportar", tags=["Gestão financeira"])
def aportar(meta_id: str, dados: Aporte, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        try:
            return metas.aportar(con, cid, meta_id, dados.valor)
        except conta.SaldoInsuficiente as e:
            raise HTTPException(400, str(e))


# ---------------- Notificações
@app.get("/notificacoes", tags=["Notificações"])
def listar_notificacoes(nao_lidas: bool = False, cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return notificacoes.listar(con, cid, nao_lidas)


@app.post("/notificacoes/marcar-lidas", tags=["Notificações"])
def marcar_lidas(cid: str = Depends(cliente_logado)):
    with conexao() as con:
        notificacoes.marcar_lidas(con, cid)
    return {"ok": True}


# ---------------- Modo demonstração (para a apresentação)
@app.post("/demo/cliente", tags=["Demonstração"])
def demo_cliente():
    with conexao() as con:
        return simulacao.criar_cliente_demo(con)


@app.post("/demo/simular-mes", tags=["Demonstração"])
def demo_mes(dados: DemoMes):
    with conexao() as con:
        return simulacao.simular_mes(con, dados.cliente_id, dados.comportamento)


@app.post("/demo/simular-mes-logado", tags=["Demonstração"])
def demo_mes_logado(comportamento: Literal["em_dia", "atrasa"] = "em_dia", cid: str = Depends(cliente_logado)):
    with conexao() as con:
        return simulacao.simular_mes(con, cid, comportamento)


@app.post("/demo/resetar", tags=["Demonstração"])
def demo_resetar():
    with conexao() as con:
        simulacao.resetar_tudo(con)
    return {"ok": True, "mensagem": "Dados de clientes apagados e relógio zerado"}
