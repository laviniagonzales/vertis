-- =====================================================================
-- VÉRTIS - Dados iniciais (parâmetros do negócio)
--
-- Tudo aqui é PROPOSTA para o grupo ajustar. Como o roteiro diz,
-- as regras ficam no banco para a equipe mudar SEM mexer no código.
-- Rode este arquivo depois do 01_schema.sql e do 02_credenciais.sql.
-- =====================================================================

SET NAMES utf8mb4;
USE vertis;

-- ---------------------------------------------------------------------
-- NÍVEIS (jornada de ascensão)
-- O cliente sobe de nível acumulando XP. Cada nível multiplica os
-- pontos ganhos (ex.: 1.25 = 25% a mais de pontos).
-- Nomes inspirados no mockup ("Nível 3 (Ascensão)", "VIP Nacional").
-- ---------------------------------------------------------------------
INSERT INTO niveis (ordem, nome, xp_minimo, multiplicador_pontos, cor_hex) VALUES
 (1, 'Semente',           0,    1.00, '#9AA0B4'),
 (2, 'Broto',             600,  1.10, '#4CC38A'),
 (3, 'Ascensão',          1500, 1.25, '#A78BFA'),
 (4, 'VIP Nacional',      3000, 1.50, '#F5B83D'),
 (5, 'VIP Internacional', 5500, 1.75, '#F472B6'),
 (6, 'Vértice',           9000, 2.00, '#38BDF8');

-- ---------------------------------------------------------------------
-- PARCEIROS (fictícios)
-- ---------------------------------------------------------------------
INSERT INTO parceiros (nome, tipo, taxa_conversao) VALUES
 ('Voe Alto Linhas Aéreas', 'companhia_aerea',     1.00),
 ('Rede Lounge Brasil',     'sala_vip',            NULL),
 ('Mercado Bom Preço',      'varejo',              NULL),
 ('Programa Milhas Mais',   'programa_fidelidade', 2.00);

-- ---------------------------------------------------------------------
-- BENEFÍCIOS
-- valor: % (multiplicador, cashback, aumento_limite, desconto)
-- ---------------------------------------------------------------------
INSERT INTO beneficios (nome, tipo, parceiro_id, nivel_minimo_id, usos_por_mes, valor) VALUES
 ('Sala VIP Aeroporto', 'sala_vip',
    (SELECT id FROM parceiros WHERE nome = 'Rede Lounge Brasil'),
    (SELECT id FROM niveis WHERE ordem = 4), 2, NULL),
 ('Multiplicador de Pontos', 'multiplicador', NULL, NULL, NULL, 25.00),
 ('Cashback 1%', 'cashback', NULL, (SELECT id FROM niveis WHERE ordem = 3), NULL, 1.00),
 ('Bônus de limite Ascensão', 'aumento_limite', NULL, (SELECT id FROM niveis WHERE ordem = 3), NULL, 10.00),
 ('Isenção de tarifas', 'isencao_tarifa', NULL, NULL, NULL, 100.00),
 ('Desconto em passagens', 'desconto_parceiro',
    (SELECT id FROM parceiros WHERE nome = 'Voe Alto Linhas Aéreas'),
    (SELECT id FROM niveis WHERE ordem = 5), NULL, 10.00);

-- ---------------------------------------------------------------------
-- CONQUISTAS
-- criterio_tipo_evento + criterio_quantidade = "faça X, N vezes".
-- Conquista sem critério de evento = é ganha ao chegar no nível mínimo.
-- ---------------------------------------------------------------------
INSERT INTO conquistas (codigo, nome, descricao, categoria, criterio_tipo_evento, criterio_quantidade,
                        nivel_minimo_id, xp_recompensa, pontos_recompensa, beneficio_id) VALUES
 ('PRIMEIRO_ACESSO', 'Primeiro Passo', 'Acesse o app pela primeira vez',
   'uso', 'acesso_app', 1, NULL, 50, 50, NULL),
 ('FATURA_EM_DIA_1', 'Fatura em Dia', 'Pague sua primeira fatura até o vencimento',
   'pagamento', 'fatura_paga_em_dia', 1, NULL, 100, 200, NULL),
 ('FATURA_EM_DIA_3', 'Pagador Pontual', 'Pague 3 faturas em dia',
   'pagamento', 'fatura_paga_em_dia', 3, NULL, 300, 500,
   (SELECT id FROM beneficios WHERE nome = 'Multiplicador de Pontos')),
 ('FATURA_EM_DIA_6', 'Fatura em Dia 6x', 'Pague 6 faturas em dia',
   'pagamento', 'fatura_paga_em_dia', 6, NULL, 600, 1000,
   (SELECT id FROM beneficios WHERE nome = 'Isenção de tarifas')),
 ('SALARIO_VERTIS', 'Salário na Vértis', 'Receba seu salário na Vértis 3 vezes',
   'uso', 'salario_recebido', 3, NULL, 200, 300, NULL),
 ('CLIENTE_ATIVO', 'Cliente Ativo', 'Faça 20 compras com o cartão',
   'uso', 'compra_realizada', 20, NULL, 150, 200, NULL),
 ('OPEN_FINANCE', 'Open Finance Conectado', 'Conecte uma conta de outro banco',
   'credito', 'open_finance_conectado', 1, NULL, 200, 300, NULL),
 ('PRIMEIRA_META', 'Primeira Meta', 'Atinja sua primeira meta financeira',
   'educacao_financeira', 'meta_atingida', 1, NULL, 200, 300, NULL),
 ('CREDITO_RESPONSAVEL', 'Crédito Responsável', 'Pague 3 parcelas de empréstimo',
   'credito', 'parcela_paga', 3, NULL, 200, 300, NULL),
 ('NIVEL_VIP_NACIONAL', 'Nível VIP Nacional', 'Chegue ao nível VIP Nacional e libere a Sala VIP',
   'viagem', NULL, 1, (SELECT id FROM niveis WHERE ordem = 4), 0, 1000,
   (SELECT id FROM beneficios WHERE nome = 'Sala VIP Aeroporto'));

-- ---------------------------------------------------------------------
-- REGRAS DE PONTUAÇÃO (quanto cada comportamento rende)
-- limite_diario evita abuso (ex.: abrir o app 50 vezes no dia).
-- Eventos negativos (fatura_atrasada, saldo_negativo) não rendem nada.
-- ---------------------------------------------------------------------
INSERT INTO regras_pontuacao (tipo_evento, xp_ganho, pontos_ganhos, milhas_ganhas, pontos_por_real, limite_diario) VALUES
 ('fatura_paga_em_dia',     300, 500, 1500, NULL, NULL),
 ('salario_recebido',       100, 100, 0,    NULL, NULL),
 ('deposito_recebido',      20,  10,  0,    NULL, 5),
 ('compra_realizada',       5,   0,   0,    1.00, 20),
 ('acesso_app',             10,  5,   0,    NULL, 1),
 ('meta_atingida',          200, 300, 500,  NULL, NULL),
 ('open_finance_conectado', 400, 500, 1000, NULL, 1),
 ('parcela_paga',           150, 200, 300,  NULL, NULL);

-- ---------------------------------------------------------------------
-- REGRAS DE PROGRESSÃO DE CRÉDITO (o coração da Vértis)
-- Na revisão do limite, o sistema escolhe a MELHOR regra que o
-- cliente cumpre e aumenta o limite pelo percentual, até o teto.
-- ---------------------------------------------------------------------
INSERT INTO regras_progressao_credito (nome, score_minimo, faturas_em_dia_minimas, meses_minimos, percentual_aumento, limite_maximo) VALUES
 ('Primeira fatura em dia', 400, 1,  0,  30.00, 1500.00),
 ('3 faturas em dia',       500, 3,  3,  50.00, 3500.00),
 ('6 faturas em dia',       600, 6,  6,  40.00, 6000.00),
 ('Cliente de confiança',   750, 10, 10, 30.00, 15000.00);

-- ---------------------------------------------------------------------
-- CATEGORIAS PADRÃO (cliente_id vazio = vale para todos)
-- ---------------------------------------------------------------------
INSERT INTO categorias (nome, tipo, icone, cor_hex) VALUES
 ('Alimentação',       'despesa', 'food',      '#F97316'),
 ('Transporte',        'despesa', 'car',       '#3B82F6'),
 ('Moradia',           'despesa', 'home',      '#8B5CF6'),
 ('Saúde',             'despesa', 'health',    '#EF4444'),
 ('Lazer',             'despesa', 'fun',       '#EC4899'),
 ('Educação',          'despesa', 'book',      '#14B8A6'),
 ('Compras',           'despesa', 'bag',       '#EAB308'),
 ('Contas e serviços', 'despesa', 'bill',      '#64748B'),
 ('Transferências',    'despesa', 'transfer',  '#94A3B8'),
 ('Salário',           'receita', 'money',     '#22C55E'),
 ('Outras receitas',   'receita', 'plus',      '#10B981');

-- ---------------------------------------------------------------------
-- INSTITUIÇÕES DO OPEN FINANCE
-- ---------------------------------------------------------------------
INSERT INTO instituicoes_financeiras (nome, codigo_banco, cnpj) VALUES
 ('Banco do Brasil', '001', '00000000000191'),
 ('Itaú Unibanco',   '341', '60701190000104'),
 ('Bradesco',        '237', '60746948000112'),
 ('Caixa',           '104', '00360305000104'),
 ('Nubank',          '260', '18236120000158');
