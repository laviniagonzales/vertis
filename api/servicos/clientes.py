"""
CLIENTES E IDENTIDADE (módulo 1) + LOGIN (módulo 9)
==================================================
O cadastro é onde a jornada começa. Num só passo (uma transação de banco):
cliente → endereço → consentimentos LGPD → senha → conta → chave Pix →
cartões → limite inicial → perfil → score inicial → progresso (nível 1).
"""
from datetime import date, timedelta
from decimal import Decimal

import relogio
from db import consultar, consultar_um, executar, inserir, auditar
from servicos import cartao, conta as conta_srv, credito, eventos, gamificacao, seguranca

FINALIDADES_LGPD = ["analise_credito", "marketing", "compartilhamento_parceiros", "uso_dados_comportamentais"]
VERSAO_TERMO = "2026.1"
MAX_TENTATIVAS = 5


class ErroCadastro(ValueError):
    pass


def _idade(nascimento: date, hoje: date) -> int:
    return hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))


def cadastrar(con, dados: dict) -> dict:
    cpf = "".join(c for c in dados["cpf"] if c.isdigit())
    hoje = relogio.hoje()

    # ---- validações (regras de negócio do cadastro)
    if not seguranca.cpf_valido(cpf):
        raise ErroCadastro("CPF inválido")
    nascimento = dados["data_nascimento"]
    if isinstance(nascimento, str):
        nascimento = date.fromisoformat(nascimento)
    if _idade(nascimento, hoje) < 18:
        raise ErroCadastro("É preciso ter 18 anos ou mais")
    if consultar_um(con, "SELECT id FROM clientes WHERE cpf=%s OR email=%s", (cpf, dados["email"])):
        raise ErroCadastro("CPF ou e-mail já cadastrado")
    if len(dados["senha"]) < 6:
        raise ErroCadastro("A senha precisa ter pelo menos 6 caracteres")
    consent = dados.get("consentimentos", {})
    if not consent.get("analise_credito") or not consent.get("uso_dados_comportamentais"):
        raise ErroCadastro("Para receber crédito progressivo, autorize a análise de crédito "
                           "e o uso de dados de comportamento")

    agora = relogio.agora()
    cliente_id = inserir(con, "clientes", {
        "nome_completo": dados["nome_completo"].strip(), "nome_social": dados.get("nome_social"),
        "cpf": cpf, "data_nascimento": nascimento, "email": dados["email"].strip().lower(),
        "telefone": dados["telefone"], "renda_mensal_declarada": dados.get("renda_mensal_declarada"),
        "ocupacao": dados.get("ocupacao"), "tipo_renda": dados.get("tipo_renda", "sem_renda"),
        "status_cadastro": "aprovado", "status_kyc": "pendente", "aceite_termos_em": agora})

    if dados.get("endereco"):
        inserir(con, "enderecos", {"cliente_id": cliente_id, **dados["endereco"]})

    for finalidade in FINALIDADES_LGPD:
        inserir(con, "consentimentos_lgpd", {
            "cliente_id": cliente_id, "finalidade": finalidade, "concedido": bool(consent.get(finalidade)),
            "versao_termo": VERSAO_TERMO, "concedido_em": agora})

    inserir(con, "credenciais", {"cliente_id": cliente_id, "senha_hash": seguranca.gerar_hash_senha(dados["senha"])})

    # ---- conta digital + Pix + cartões
    numero, digito = conta_srv.gerar_numero_conta(con)
    conta_id = inserir(con, "contas", {"cliente_id": cliente_id, "numero_conta": numero, "digito": digito,
                                       "aberta_em": agora})
    inserir(con, "chaves_pix", {"conta_id": conta_id, "tipo_chave": "cpf", "valor_chave": cpf})
    inserir(con, "chaves_pix", {"conta_id": conta_id, "tipo_chave": "email", "valor_chave": dados["email"].lower()})
    nome_cartao = (dados.get("nome_social") or dados["nome_completo"]).split()
    nome_cartao = f"{nome_cartao[0]} {nome_cartao[-1]}" if len(nome_cartao) > 1 else nome_cartao[0]
    cartao.emitir(con, conta_id, nome_cartao, formato="virtual", status="ativo")
    cartao.emitir(con, conta_id, nome_cartao, formato="fisico", status="solicitado")

    # ---- crédito: limite inicial pequeno e seguro
    limite = credito.limite_inicial(dados.get("renda_mensal_declarada"), dados.get("tipo_renda"))
    # proxima_revisao_em vazia = a 1ª fatura paga em dia já dispara a revisão
    inserir(con, "limites_credito", {"cliente_id": cliente_id, "limite_total": limite, "limite_disponivel": limite,
                                     "proxima_revisao_em": None})
    inserir(con, "historico_limite", {"cliente_id": cliente_id, "limite_anterior": 0, "limite_novo": limite,
                                      "motivo": "aumento_automatico", "alterado_em": agora})
    inserir(con, "perfil_financeiro", {"cliente_id": cliente_id})

    # ---- gamificação: começa no nível 1, todas as conquistas em andamento
    nivel1 = consultar_um(con, "SELECT id, xp_minimo FROM niveis ORDER BY ordem LIMIT 1")
    nivel2 = consultar_um(con, "SELECT xp_minimo FROM niveis ORDER BY ordem LIMIT 1 OFFSET 1")
    inserir(con, "progresso_cliente", {"cliente_id": cliente_id, "nivel_id": nivel1["id"],
                                       "xp_para_proximo_nivel": nivel2["xp_minimo"] if nivel2 else 0})
    for c in consultar(con, "SELECT id, nivel_minimo_id FROM conquistas WHERE ativa=TRUE"):
        inserir(con, "conquistas_cliente", {"cliente_id": cliente_id, "conquista_id": c["id"],
                                            "status": "em_andamento"})

    credito.atualizar_perfil(con, cliente_id)
    credito.calcular_score(con, cliente_id)
    credito.atualizar_previsoes(con, cliente_id)
    gamificacao.atualizar_proxima_conquista(con, cliente_id)
    auditar(con, "cadastrou_cliente", "clientes", cliente_id, None, {"cpf_final": cpf[-4:]},
            ator_tipo="cliente", ator_id=cliente_id)
    return {"cliente_id": cliente_id, "conta": f"{numero}-{digito}", "limite_inicial": float(limite)}


def login(con, cpf: str, senha: str, dispositivo: dict | None = None, ip: str | None = None) -> dict:
    cpf = "".join(c for c in cpf if c.isdigit())
    cli = consultar_um(con, """SELECT c.id, c.status_cadastro, cr.senha_hash, cr.tentativas_falhas, cr.bloqueada_ate
                                FROM clientes c JOIN credenciais cr ON cr.cliente_id = c.id
                               WHERE c.cpf=%s AND c.excluido_em IS NULL""", (cpf,))
    if not cli:
        raise PermissionError("CPF ou senha incorretos")
    agora = relogio.agora()
    if cli["bloqueada_ate"] and cli["bloqueada_ate"] > agora:
        raise PermissionError("Acesso bloqueado temporariamente por excesso de tentativas")

    disp_id = None
    if dispositivo:
        d = consultar_um(con, """SELECT id FROM dispositivos WHERE cliente_id=%s AND identificador_dispositivo=%s""",
                         (cli["id"], dispositivo["identificador"]))
        if d:
            disp_id = d["id"]
            executar(con, "UPDATE dispositivos SET ultimo_acesso_em=%s WHERE id=%s", (agora, disp_id))
        else:
            disp_id = inserir(con, "dispositivos", {
                "cliente_id": cli["id"], "identificador_dispositivo": dispositivo["identificador"],
                "modelo": dispositivo.get("modelo"), "sistema_operacional": dispositivo.get("sistema"),
                "confiavel": True, "ultimo_acesso_em": agora})

    ok = seguranca.conferir_senha(senha, cli["senha_hash"])
    inserir(con, "sessoes_acesso", {"cliente_id": cli["id"], "dispositivo_id": disp_id, "ip": ip,
                                    "metodo_login": "senha", "sucesso": ok, "iniciada_em": agora})
    if not ok:
        falhas = cli["tentativas_falhas"] + 1
        bloqueio = agora + timedelta(minutes=15) if falhas >= MAX_TENTATIVAS else None
        executar(con, "UPDATE credenciais SET tentativas_falhas=%s, bloqueada_ate=%s WHERE cliente_id=%s",
                 (0 if bloqueio else falhas, bloqueio, cli["id"]))
        con.commit()   # grava a tentativa falha ANTES do erro (senão o rollback apagaria)
        raise PermissionError("CPF ou senha incorretos")

    executar(con, "UPDATE credenciais SET tentativas_falhas=0, bloqueada_ate=NULL WHERE cliente_id=%s", (cli["id"],))
    registrar_acesso(con, cli["id"])
    return {"token": seguranca.gerar_token(cli["id"]), "cliente_id": cli["id"]}


def registrar_acesso(con, cliente_id):
    """Evento 'acesso_app' + sequência de dias ativos (para gamificação)."""
    hoje = relogio.hoje()
    ultimo = consultar_um(con, """SELECT MAX(DATE(ocorrido_em)) AS d FROM eventos_comportamentais
                                   WHERE cliente_id=%s AND tipo_evento='acesso_app'""", (cliente_id,))["d"]
    if ultimo == hoje:
        return
    seq = "sequencia_dias_ativos + 1" if ultimo == hoje - timedelta(days=1) else "1"
    executar(con, f"UPDATE progresso_cliente SET sequencia_dias_ativos = {seq} WHERE cliente_id=%s", (cliente_id,))
    eventos.registrar(con, cliente_id, "acesso_app", "app")


def resumo(con, cliente_id) -> dict:
    """Tudo que a TELA DE EVOLUÇÃO precisa, numa chamada só."""
    cli = consultar_um(con, """SELECT nome_completo, nome_social, cpf, email FROM clientes WHERE id=%s""", (cliente_id,))
    prog = gamificacao.progresso(con, cliente_id)
    proximo_nivel = consultar_um(con, "SELECT nome, xp_minimo FROM niveis WHERE ordem=%s", (prog["nivel_ordem"] + 1,))
    nivel_atual = consultar_um(con, "SELECT xp_minimo FROM niveis WHERE ordem=%s", (prog["nivel_ordem"],))
    lim = consultar_um(con, "SELECT * FROM limites_credito WHERE cliente_id=%s", (cliente_id,))
    score = credito.ultimo_score(con, cliente_id)
    perfil = consultar_um(con, "SELECT perfil_risco, faturas_pagas_em_dia FROM perfil_financeiro WHERE cliente_id=%s",
                          (cliente_id,))
    conta = conta_srv.conta_do_cliente(con, cliente_id)
    proxima = None
    if prog["proxima_conquista_id"]:
        proxima = consultar_um(con, """
            SELECT c.nome, c.descricao, c.criterio_quantidade, cc.progresso_atual
              FROM conquistas c JOIN conquistas_cliente cc ON cc.conquista_id=c.id AND cc.cliente_id=%s
             WHERE c.id=%s""", (cliente_id, prog["proxima_conquista_id"]))
    destaques = consultar(con, """
        SELECT c.codigo, c.nome, c.categoria, cc.conquistada_em FROM conquistas_cliente cc
          JOIN conquistas c ON c.id = cc.conquista_id
         WHERE cc.cliente_id=%s AND cc.status='conquistada' ORDER BY cc.conquistada_em DESC LIMIT 3""", (cliente_id,))
    beneficios = consultar(con, """
        SELECT b.nome, b.tipo, bc.codigo_voucher, bc.usos_restantes, bc.liberado_em FROM beneficios_cliente bc
          JOIN beneficios b ON b.id = bc.beneficio_id
         WHERE bc.cliente_id=%s AND bc.status='liberado' ORDER BY bc.liberado_em DESC""", (cliente_id,))
    # Histórico do limite = os pontos da "trilha de ascensão" desenhada no app
    trilha = consultar(con, """SELECT limite_novo AS valor, motivo, alterado_em AS data FROM historico_limite
                                WHERE cliente_id=%s ORDER BY alterado_em, criado_em""", (cliente_id,))
    return {
        "nome": (cli["nome_social"] or cli["nome_completo"]),
        "nivel": {"ordem": prog["nivel_ordem"], "nome": prog["nivel_nome"], "cor": prog["nivel_cor"],
                  "multiplicador": prog["multiplicador_pontos"],
                  "xp_total": prog["xp_total"], "xp_nivel_atual": nivel_atual["xp_minimo"],
                  "xp_proximo_nivel": proximo_nivel["xp_minimo"] if proximo_nivel else None,
                  "proximo_nivel": proximo_nivel["nome"] if proximo_nivel else None},
        "pontos": prog["saldo_pontos"], "milhas": prog["saldo_milhas"],
        "sequencia_dias": prog["sequencia_dias_ativos"],
        "saldo_conta": conta["saldo_disponivel"],
        "conta": f"{conta['agencia']} / {conta['numero_conta']}-{conta['digito']}",
        "limite": {"total": lim["limite_total"], "utilizado": lim["limite_utilizado"],
                   "disponivel": lim["limite_disponivel"], "previsto": lim["proximo_limite_previsto"],
                   "proxima_revisao": lim["proxima_revisao_em"],
                   "emprestimo_pre_aprovado": lim["limite_emprestimo_pre_aprovado"]},
        "score": score["score_interno"], "perfil_risco": perfil["perfil_risco"],
        "faturas_em_dia": perfil["faturas_pagas_em_dia"],
        "proxima_conquista": proxima, "conquistas_recentes": destaques,
        "beneficios": beneficios, "trilha": trilha,
        "data_simulada": relogio.agora(),
    }
