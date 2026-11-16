"""
MODO DEMONSTRAÇÃO
=================
Para a apresentação: cria o cliente "Gabriel" (sem histórico) e simula
um MÊS de vida financeira em poucos segundos, avançando o relógio dia a dia:

   dia 5   → recebe o salário via Pix          (evento salario_recebido)
   dia 6   → guarda R$ 300 na meta             (pode gerar meta_atingida)
   dia 7   → paga o aluguel via Pix
   dia 10  → paga luz, água e celular (contas de consumo → ajudam o score)
   vários  → compras no cartão                 (evento compra_realizada)
   todo dia→ abre o app (quase sempre)         (evento acesso_app)
   fatura  → fecha 7 dias antes do vencimento; ele paga 2 dias antes
             (evento fatura_paga_em_dia → limite sobe!)

Com comportamento="atrasa", ele paga a fatura 5 dias DEPOIS do vencimento,
para mostrar o lado negativo (limite reduzido, score cai).
"""
import random
from datetime import timedelta
from decimal import Decimal

import relogio
from db import consultar, consultar_um, executar
from servicos import cartao, clientes, conta as conta_srv, credito, gamificacao, metas, seguranca

D = Decimal
LOJAS = [("Mercado Bom Preço", "Alimentação", (40, 180)), ("Posto Avenida", "Transporte", (50, 120)),
         ("Farmácia Saúde+", "Saúde", (20, 90)), ("Lanchonete da Esquina", "Alimentação", (15, 45)),
         ("Livraria Saber", "Educação", (30, 90)), ("Cinema Center", "Lazer", (25, 60)),
         ("Loja Moda Já", "Compras", (60, 200)), ("App de Transporte", "Transporte", (12, 40))]

# Tabelas com dados de clientes (as de parâmetros — níveis, regras, categorias... — ficam)
TABELAS_DE_CLIENTES = [
    "notificacoes", "logs_auditoria", "sessoes_acesso", "dispositivos", "movimentacoes_recompensa", "resgates",
    "beneficios_cliente", "conquistas_cliente", "progresso_cliente", "metas_financeiras", "orcamentos",
    "transacoes_externas", "contas_externas", "consentimentos_open_finance", "parcelas_emprestimo",
    "contratos_emprestimo", "propostas_emprestimo", "historico_limite", "limites_credito", "scores_credito",
    "perfil_financeiro", "eventos_comportamentais", "lancamentos_fatura", "faturas", "compras_cartao", "cartoes",
    "boletos", "favorecidos", "chaves_pix", "transacoes", "contas", "credenciais", "consentimentos_lgpd",
    "documentos_cliente", "enderecos", "clientes"]


def criar_cliente_demo(con, nome="Gabriel Silva", renda=2500) -> dict:
    n = consultar_um(con, "SELECT COUNT(*) AS n FROM clientes")["n"]
    cpf = seguranca.gerar_cpf_valido(123_456_000 + n * 7 + 1)
    primeiro = nome.split()[0].lower()
    dados = {
        "nome_completo": nome, "cpf": cpf, "data_nascimento": "2003-04-15",
        "email": f"{primeiro}{n + 1}@demo.vertis.com", "telefone": "11988887777",
        "renda_mensal_declarada": renda, "ocupacao": "Entregador por aplicativo", "tipo_renda": "informal",
        "senha": "123456",
        "consentimentos": {"analise_credito": True, "uso_dados_comportamentais": True,
                           "marketing": False, "compartilhamento_parceiros": True},
        "endereco": {"cep": "05858001", "logradouro": "Estrada de Itapecerica", "numero": "5859",
                     "bairro": "Jardim IAE", "cidade": "São Paulo", "uf": "SP"},
    }
    r = clientes.cadastrar(con, dados)
    metas.criar(con, r["cliente_id"], "Reserva de emergência", 1500)
    clientes.registrar_acesso(con, r["cliente_id"])
    return {**r, "cpf": cpf, "senha": "123456", "nome": nome}


def _foto(con, cliente_id):
    lim = consultar_um(con, "SELECT limite_total FROM limites_credito WHERE cliente_id=%s", (cliente_id,))
    prog = gamificacao.progresso(con, cliente_id)
    return {"limite": float(lim["limite_total"]), "score": credito.ultimo_score(con, cliente_id)["score_interno"],
            "nivel": prog["nivel_nome"], "xp": prog["xp_total"], "pontos": prog["saldo_pontos"],
            "milhas": prog["saldo_milhas"]}


def simular_mes(con, cliente_id, comportamento="em_dia", dias=30) -> dict:
    antes = _foto(con, cliente_id)
    inicio = relogio.agora()
    renda = D(str(consultar_um(con, "SELECT renda_mensal_declarada AS r FROM clientes WHERE id=%s",
                               (cliente_id,))["r"] or 1500))
    rnd = random.Random(f"{cliente_id}{relogio.deslocamento_dias()}")
    meta = consultar_um(con, """SELECT id FROM metas_financeiras WHERE cliente_id=%s AND status='ativa'
                                 ORDER BY criado_em LIMIT 1""", (cliente_id,))
    dias_compra = set(rnd.sample(range(1, dias + 1), 10))

    for dia in range(1, dias + 1):
        relogio.avancar(1)
        hoje = relogio.hoje()
        cartao.processar_ciclo(con, cliente_id)
        if rnd.random() < 0.85:
            clientes.registrar_acesso(con, cliente_id)

        if hoje.day == 5:
            conta_srv.receber(con, cliente_id, renda, "Plataforma de Entregas LTDA", "12345678000199", eh_salario=True)
        if hoje.day == 6 and meta:
            try:
                metas.aportar(con, cliente_id, meta["id"], 300)
            except Exception:
                pass
        if hoje.day == 7:
            try:
                conta_srv.pix_enviar(con, cliente_id, "aluguel@imobiliaria.com", (renda * D("0.32")).quantize(D("1")),
                                     "Aluguel")
            except conta_srv.SaldoInsuficiente:
                pass

        if hoje.day == 10:   # contas de consumo (luz, água, celular), pagas no vencimento
            for nome, fracao in (("Energia elétrica", "0.06"), ("Água e esgoto", "0.03"), ("Celular / internet", "0.03")):
                try:
                    venc = hoje if comportamento == "em_dia" else hoje - timedelta(days=5)
                    conta_srv.pagar_conta(con, cliente_id, nome, (renda * D(fracao)).quantize(D("0.01")), venc)
                except conta_srv.SaldoInsuficiente:
                    pass

        if dia in dias_compra:
            lim = consultar_um(con, "SELECT limite_total, limite_disponivel FROM limites_credito WHERE cliente_id=%s",
                               (cliente_id,))
            loja, cat, (vmin, vmax) = rnd.choice(LOJAS)
            teto = float(lim["limite_total"]) * 0.06        # usa uns 35-40% do limite no mês
            valor = round(min(rnd.uniform(vmin, vmax), max(teto, 15)), 2)
            if float(lim["limite_disponivel"]) >= valor:
                cartao.comprar(con, cliente_id, valor, loja, categoria=cat)

        # Pagamento da fatura
        for f in consultar(con, """SELECT * FROM faturas WHERE cliente_id=%s
                                    AND status IN ('fechada','paga_parcial','atrasada')""", (cliente_id,)):
            dias_ate_venc = (f["data_vencimento"] - hoje).days
            if (comportamento == "em_dia" and dias_ate_venc <= 2) or \
               (comportamento == "atrasa" and dias_ate_venc <= -5):
                try:
                    cartao.pagar_fatura(con, cliente_id, f["id"])
                except conta_srv.SaldoInsuficiente:
                    pass

    novidades = consultar(con, """SELECT tipo, titulo, mensagem FROM notificacoes
                                   WHERE cliente_id=%s AND enviada_em > %s ORDER BY enviada_em""",
                          (cliente_id, inicio))
    return {"de": inicio.date(), "ate": relogio.hoje(), "antes": antes, "depois": _foto(con, cliente_id),
            "novidades": novidades}


def resetar_tudo(con):
    """Apaga TODOS os dados de clientes (mantém os parâmetros) e zera o relógio."""
    executar(con, "SET FOREIGN_KEY_CHECKS = 0")
    for t in TABELAS_DE_CLIENTES:
        executar(con, f"DELETE FROM {t}")
    executar(con, "DELETE FROM categorias WHERE cliente_id IS NOT NULL")
    executar(con, "SET FOREIGN_KEY_CHECKS = 1")
    relogio.resetar()
