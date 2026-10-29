"""
CONTA DIGITAL (módulo 2 do roteiro)
==================================
A tabela `transacoes` é o EXTRATO ÚNICO: todo dinheiro que entra ou sai
passa por ela, e o saldo da conta é atualizado na mesma operação.
"""
import random
from decimal import Decimal

import relogio
from db import consultar, consultar_um, executar, inserir
from servicos import eventos

D = Decimal


class SaldoInsuficiente(Exception):
    pass


def gerar_numero_conta(con) -> tuple[str, str]:
    """Número de 8 dígitos + dígito verificador (módulo 11), único no banco."""
    while True:
        numero = f"{random.randint(10_000_000, 99_999_999)}"
        soma = sum(int(d) * p for d, p in zip(reversed(numero), range(2, 10)))
        digito = str((11 - soma % 11) % 10)
        if not consultar_um(con, "SELECT id FROM contas WHERE numero_conta=%s", (numero,)):
            return numero, digito


def conta_do_cliente(con, cliente_id) -> dict:
    return consultar_um(con, """SELECT * FROM contas WHERE cliente_id=%s AND status <> 'encerrada'
                                 ORDER BY aberta_em LIMIT 1""", (cliente_id,))


def categoria_id(con, nome: str | None):
    if not nome:
        return None
    c = consultar_um(con, "SELECT id FROM categorias WHERE nome=%s AND cliente_id IS NULL", (nome,))
    return c["id"] if c else None


def lancar(con, conta_id, tipo, direcao, valor, descricao, categoria=None,
           contraparte_nome=None, contraparte_documento=None, contraparte_banco=None,
           id_externo=None, permitir_negativo=False) -> dict:
    """Lança uma transação e atualiza o saldo — as duas coisas juntas."""
    valor = D(str(valor)).quantize(D("0.01"))
    if valor <= 0:
        raise ValueError("O valor precisa ser maior que zero")
    # FOR UPDATE "tranca" a linha da conta até o fim da operação (evita 2 saques ao mesmo tempo)
    conta = consultar_um(con, "SELECT * FROM contas WHERE id=%s FOR UPDATE", (conta_id,))
    if conta["status"] != "ativa":
        raise ValueError("Conta não está ativa")
    saldo = D(conta["saldo_disponivel"])
    novo_saldo = saldo + valor if direcao == "entrada" else saldo - valor
    if novo_saldo < 0 and not permitir_negativo:
        raise SaldoInsuficiente(f"Saldo insuficiente (disponível: R$ {saldo:.2f})")

    executar(con, "UPDATE contas SET saldo_disponivel=%s WHERE id=%s", (novo_saldo, conta_id))
    t = {"conta_id": conta_id, "tipo": tipo, "direcao": direcao, "valor": valor, "saldo_apos": novo_saldo,
         "descricao": descricao[:150] if descricao else None, "categoria_id": categoria_id(con, categoria),
         "contraparte_nome": contraparte_nome, "contraparte_documento": contraparte_documento,
         "contraparte_banco": contraparte_banco, "id_externo": id_externo,
         "status": "concluida", "realizada_em": relogio.agora()}
    t["id"] = inserir(con, "transacoes", t)
    if novo_saldo < 0 <= saldo:
        eventos.registrar(con, conta["cliente_id"], "saldo_negativo", "conta", t["id"], novo_saldo)
    return t


def extrato(con, cliente_id, limite=40):
    return consultar(con, """
        SELECT t.id, t.tipo, t.direcao, t.valor, t.saldo_apos, t.descricao, t.contraparte_nome,
               t.realizada_em, cat.nome AS categoria, cat.cor_hex AS categoria_cor
          FROM transacoes t
          JOIN contas c ON c.id = t.conta_id
          LEFT JOIN categorias cat ON cat.id = t.categoria_id
         WHERE c.cliente_id = %s
         ORDER BY t.realizada_em DESC, t.criado_em DESC
         LIMIT %s""", (cliente_id, limite))


# ---------------------------------------------------------------- Pix
def _id_pix() -> str:
    """Código end-to-end do Pix (simulado): E + ISPB + data + aleatório."""
    return "E99999999" + relogio.agora().strftime("%Y%m%d%H%M") + f"{random.getrandbits(40):011x}"


def pix_enviar(con, cliente_id, chave_destino, valor, descricao=None) -> dict:
    origem = conta_do_cliente(con, cliente_id)
    chave = consultar_um(con, """
        SELECT cp.conta_id, cl.id AS cliente_id, cl.nome_completo, cl.cpf
          FROM chaves_pix cp JOIN contas c ON c.id = cp.conta_id JOIN clientes cl ON cl.id = c.cliente_id
         WHERE cp.valor_chave = %s AND cp.status = 'ativa'""", (chave_destino,))
    e2e = _id_pix()
    if chave:   # destino é cliente Vértis: o dinheiro sai de uma conta e entra na outra
        nome, doc, banco = chave["nome_completo"], chave["cpf"], "Vértis"
    else:       # destino em outro banco (simulado)
        nome, doc, banco = f"Chave {chave_destino}", None, "Outro"
    t = lancar(con, origem["id"], "pix_enviado", "saida", valor, descricao or f"Pix para {nome}",
               categoria="Transferências", contraparte_nome=nome, contraparte_documento=doc,
               contraparte_banco=banco, id_externo=e2e)
    if chave:
        remetente = consultar_um(con, "SELECT nome_completo, cpf FROM clientes WHERE id=%s", (cliente_id,))
        receber(con, chave["cliente_id"], valor, remetente["nome_completo"], remetente["cpf"],
                eh_salario=False, id_externo=e2e)
    return t


def receber(con, cliente_id, valor, de_nome, de_documento=None, eh_salario=False, id_externo=None) -> dict:
    """Pix recebido. No app, existe um botão de 'simular recebimento' para a demonstração."""
    conta = conta_do_cliente(con, cliente_id)
    t = lancar(con, conta["id"], "pix_recebido", "entrada", valor,
               "Salário" if eh_salario else f"Pix de {de_nome}",
               categoria="Salário" if eh_salario else "Outras receitas",
               contraparte_nome=de_nome, contraparte_documento=de_documento, id_externo=id_externo or _id_pix())
    eventos.registrar(con, cliente_id, "salario_recebido" if eh_salario else "deposito_recebido",
                      "conta", t["id"], valor)
    return t


def chaves(con, cliente_id):
    return consultar(con, """SELECT cp.tipo_chave, cp.valor_chave FROM chaves_pix cp
                              JOIN contas c ON c.id = cp.conta_id
                             WHERE c.cliente_id=%s AND cp.status='ativa'""", (cliente_id,))
