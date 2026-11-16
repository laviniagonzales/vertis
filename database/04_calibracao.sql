-- =====================================================================
-- VÉRTIS — 04: CALIBRAÇÃO DO CRÉDITO RESPONSÁVEL (rodar DEPOIS do 03)
-- =====================================================================
-- Por que existe: a simulação de 12 meses (api/cenarios.py) mostrou que
-- as regras antigas davam limite de 2x a renda em 8 meses e score 1000
-- para um jovem aprendiz. Para quem tem baixa renda isso abre a porta
-- do superendividamento. Esta calibração faz o limite crescer de forma
-- GRADUAL e proporcional à renda comprovada.
-- Pode rodar mais de uma vez sem problema.
-- =====================================================================
SET NAMES utf8mb4;
USE vertis;

-- ---------------------------------------------------------------------
-- 1) Contas de consumo (luz, água, celular) contam a favor do score.
--    É o histórico que quem nunca teve cartão JÁ TEM.
-- ---------------------------------------------------------------------
SET @existe = (SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = 'vertis' AND table_name = 'boletos' AND column_name = 'eh_conta_consumo');
SET @sql = IF(@existe = 0,
  'ALTER TABLE boletos ADD COLUMN eh_conta_consumo BOOLEAN NOT NULL DEFAULT FALSE AFTER beneficiario',
  'SELECT ''coluna eh_conta_consumo já existe''');
PREPARE passo FROM @sql;
EXECUTE passo;
DEALLOCATE PREPARE passo;

-- ---------------------------------------------------------------------
-- 2) Progressão do limite: aumentos menores e tetos por etapa.
--    (o teto por renda — 1x / 1,5x / 2x — fica no código: credito.py)
-- ---------------------------------------------------------------------
-- (UPDATE em vez de DELETE: o histórico de limite aponta para essas regras)
UPDATE regras_progressao_credito SET score_minimo = 400, faturas_em_dia_minimas = 1,  meses_minimos = 0,
       percentual_aumento = 20.00, limite_maximo = 600.00   WHERE nome = 'Primeira fatura em dia';
UPDATE regras_progressao_credito SET score_minimo = 480, faturas_em_dia_minimas = 3,  meses_minimos = 3,
       percentual_aumento = 15.00, limite_maximo = 1500.00  WHERE nome = '3 faturas em dia';
UPDATE regras_progressao_credito SET score_minimo = 560, faturas_em_dia_minimas = 6,  meses_minimos = 6,
       percentual_aumento = 15.00, limite_maximo = 4000.00  WHERE nome = '6 faturas em dia';
UPDATE regras_progressao_credito SET score_minimo = 700, faturas_em_dia_minimas = 12, meses_minimos = 12,
       percentual_aumento = 12.00, limite_maximo = 15000.00 WHERE nome = 'Cliente de confiança';

-- ---------------------------------------------------------------------
-- 3) Gamificação: premiar BOM comportamento, não gastar.
--    Antes: 1 ponto por real gasto no cartão (incentivava o consumo).
-- ---------------------------------------------------------------------
UPDATE regras_pontuacao SET xp_ganho = 2, pontos_ganhos = 0, pontos_por_real = NULL, limite_diario = 10
 WHERE tipo_evento = 'compra_realizada';
UPDATE regras_pontuacao SET xp_ganho = 300, pontos_ganhos = 600
 WHERE tipo_evento = 'fatura_paga_em_dia';
UPDATE regras_pontuacao SET xp_ganho = 250, pontos_ganhos = 400
 WHERE tipo_evento = 'meta_atingida';
