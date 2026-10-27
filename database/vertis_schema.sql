-- =====================================================================
-- VÉRTIS - Script de criação do banco de dados
-- MySQL 8.0 | 43 tabelas em 9 módulos
-- Baseado no documento "Vértis – Roteiro do Banco de Dados"
--
-- Convenções:
--  * Chave primária "id" CHAR(36) com UUID gerado automaticamente.
--  * Toda tabela tem criado_em e atualizado_em (preenchidos sozinhos).
--  * Dinheiro em DECIMAL(15,2), em reais.
--  * As tabelas estão em ordem: quem é referenciado vem antes.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS vertis
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE vertis;

-- =====================================================================
-- MÓDULO 1 - CLIENTES E IDENTIDADE
-- =====================================================================

CREATE TABLE clientes (
  id                      CHAR(36)      NOT NULL DEFAULT (UUID()),
  nome_completo           VARCHAR(150)  NOT NULL,
  nome_social             VARCHAR(150)  NULL,
  cpf                     CHAR(11)      NOT NULL,
  data_nascimento         DATE          NOT NULL,
  email                   VARCHAR(150)  NOT NULL,
  telefone                VARCHAR(20)   NOT NULL,
  renda_mensal_declarada  DECIMAL(15,2) NULL,
  ocupacao                VARCHAR(100)  NULL,
  tipo_renda              ENUM('formal','informal','autonomo','beneficio','sem_renda') NULL,
  status_cadastro         ENUM('em_analise','aprovado','reprovado','bloqueado','encerrado') NOT NULL DEFAULT 'em_analise',
  status_kyc              ENUM('pendente','validado','recusado') NOT NULL DEFAULT 'pendente',
  aceite_termos_em        DATETIME      NULL,
  excluido_em             DATETIME      NULL,
  criado_em               DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_clientes_cpf (cpf),
  UNIQUE KEY uk_clientes_email (email)
) ENGINE=InnoDB;

CREATE TABLE enderecos (
  id             CHAR(36)     NOT NULL DEFAULT (UUID()),
  cliente_id     CHAR(36)     NOT NULL,
  cep            CHAR(8)      NOT NULL,
  logradouro     VARCHAR(150) NOT NULL,
  numero         VARCHAR(10)  NOT NULL,
  complemento    VARCHAR(80)  NULL,
  bairro         VARCHAR(80)  NOT NULL,
  cidade         VARCHAR(80)  NOT NULL,
  uf             CHAR(2)      NOT NULL,
  tipo           ENUM('residencial','correspondencia') NOT NULL DEFAULT 'residencial',
  principal      BOOLEAN      NOT NULL DEFAULT TRUE,
  criado_em      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_enderecos_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

CREATE TABLE documentos_cliente (
  id                CHAR(36)     NOT NULL DEFAULT (UUID()),
  cliente_id        CHAR(36)     NOT NULL,
  tipo_documento    ENUM('rg','cnh','selfie','comprovante_residencia','comprovante_renda') NOT NULL,
  numero            VARCHAR(30)  NULL,
  url_arquivo       VARCHAR(255) NOT NULL,
  status_validacao  ENUM('pendente','aprovado','recusado') NOT NULL DEFAULT 'pendente',
  validado_em       DATETIME     NULL,
  criado_em         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_documentos_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

CREATE TABLE consentimentos_lgpd (
  id             CHAR(36)    NOT NULL DEFAULT (UUID()),
  cliente_id     CHAR(36)    NOT NULL,
  finalidade     ENUM('analise_credito','marketing','compartilhamento_parceiros','uso_dados_comportamentais') NOT NULL,
  concedido      BOOLEAN     NOT NULL,
  versao_termo   VARCHAR(20) NOT NULL,
  concedido_em   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  revogado_em    DATETIME    NULL,
  criado_em      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_consentlgpd_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

-- =====================================================================
-- MÓDULO 8 (criado antes) - CATEGORIAS
-- Vem aqui porque transações e compras usam categoria_id.
-- =====================================================================

CREATE TABLE categorias (
  id                CHAR(36)    NOT NULL DEFAULT (UUID()),
  nome              VARCHAR(50) NOT NULL,
  categoria_pai_id  CHAR(36)    NULL,
  cliente_id        CHAR(36)    NULL COMMENT 'Vazio = categoria padrão da Vértis',
  tipo              ENUM('despesa','receita') NOT NULL,
  icone             VARCHAR(50) NULL,
  cor_hex           CHAR(7)     NULL,
  criado_em         DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_categorias_pai     FOREIGN KEY (categoria_pai_id) REFERENCES categorias(id),
  CONSTRAINT fk_categorias_cliente FOREIGN KEY (cliente_id)       REFERENCES clientes(id)
) ENGINE=InnoDB;

-- =====================================================================
-- MÓDULO 2 - CONTA DIGITAL
-- =====================================================================

CREATE TABLE contas (
  id                CHAR(36)      NOT NULL DEFAULT (UUID()),
  cliente_id        CHAR(36)      NOT NULL,
  agencia           CHAR(4)       NOT NULL DEFAULT '0001',
  numero_conta      VARCHAR(12)   NOT NULL,
  digito            CHAR(1)       NOT NULL,
  tipo_conta        ENUM('pagamento','corrente') NOT NULL DEFAULT 'pagamento',
  saldo_disponivel  DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  saldo_bloqueado   DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  status            ENUM('ativa','bloqueada','encerrada') NOT NULL DEFAULT 'ativa',
  aberta_em         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  encerrada_em      DATETIME      NULL,
  criado_em         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_contas_numero (numero_conta),
  CONSTRAINT fk_contas_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

CREATE TABLE transacoes (
  id                     CHAR(36)      NOT NULL DEFAULT (UUID()),
  conta_id               CHAR(36)      NOT NULL,
  tipo                   ENUM('pix_enviado','pix_recebido','ted','deposito','saque','pagamento_boleto','compra_debito','pagamento_fatura','credito_emprestimo','pagamento_parcela','tarifa','estorno') NOT NULL,
  direcao                ENUM('entrada','saida') NOT NULL,
  valor                  DECIMAL(15,2) NOT NULL,
  saldo_apos             DECIMAL(15,2) NOT NULL,
  descricao              VARCHAR(150)  NULL,
  categoria_id           CHAR(36)      NULL,
  contraparte_nome       VARCHAR(150)  NULL,
  contraparte_documento  VARCHAR(14)   NULL,
  contraparte_banco      VARCHAR(10)   NULL,
  id_externo             VARCHAR(64)   NULL COMMENT 'Ex.: código end-to-end do Pix',
  status                 ENUM('pendente','concluida','falhou','estornada') NOT NULL DEFAULT 'pendente',
  realizada_em           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  criado_em              DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_transacoes_conta_data (conta_id, realizada_em),
  CONSTRAINT chk_transacoes_valor CHECK (valor > 0),
  CONSTRAINT fk_transacoes_conta     FOREIGN KEY (conta_id)     REFERENCES contas(id),
  CONSTRAINT fk_transacoes_categoria FOREIGN KEY (categoria_id) REFERENCES categorias(id)
) ENGINE=InnoDB;

CREATE TABLE chaves_pix (
  id             CHAR(36)    NOT NULL DEFAULT (UUID()),
  conta_id       CHAR(36)    NOT NULL,
  tipo_chave     ENUM('cpf','email','telefone','aleatoria') NOT NULL,
  valor_chave    VARCHAR(77) NOT NULL,
  status         ENUM('ativa','portabilidade','excluida') NOT NULL DEFAULT 'ativa',
  criado_em      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_chaves_pix_valor (valor_chave),
  CONSTRAINT fk_chavespix_conta FOREIGN KEY (conta_id) REFERENCES contas(id)
) ENGINE=InnoDB;

CREATE TABLE boletos (
  id               CHAR(36)      NOT NULL DEFAULT (UUID()),
  conta_id         CHAR(36)      NOT NULL,
  linha_digitavel  VARCHAR(48)   NOT NULL,
  beneficiario     VARCHAR(150)  NOT NULL,
  valor            DECIMAL(15,2) NOT NULL,
  vencimento       DATE          NOT NULL,
  status           ENUM('agendado','pago','vencido','cancelado') NOT NULL DEFAULT 'agendado',
  pago_em          DATETIME      NULL,
  transacao_id     CHAR(36)      NULL,
  criado_em        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_boletos_conta     FOREIGN KEY (conta_id)     REFERENCES contas(id),
  CONSTRAINT fk_boletos_transacao FOREIGN KEY (transacao_id) REFERENCES transacoes(id)
) ENGINE=InnoDB;

CREATE TABLE favorecidos (
  id             CHAR(36)     NOT NULL DEFAULT (UUID()),
  cliente_id     CHAR(36)     NOT NULL,
  nome           VARCHAR(150) NOT NULL,
  documento      VARCHAR(14)  NOT NULL,
  chave_pix      VARCHAR(77)  NULL,
  banco          VARCHAR(10)  NULL,
  agencia        VARCHAR(5)   NULL,
  conta          VARCHAR(15)  NULL,
  criado_em      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_favorecidos_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

-- =====================================================================
-- MÓDULO 3 - CARTÕES
-- =====================================================================

CREATE TABLE cartoes (
  id                      CHAR(36)    NOT NULL DEFAULT (UUID()),
  conta_id                CHAR(36)    NOT NULL,
  formato                 ENUM('fisico','virtual','virtual_temporario') NOT NULL,
  funcao                  ENUM('debito','credito','multiplo') NOT NULL,
  bandeira                VARCHAR(20) NOT NULL,
  final_cartao            CHAR(4)     NOT NULL COMMENT 'Só os 4 últimos dígitos',
  token_processador       VARCHAR(64) NOT NULL COMMENT 'Número completo fica no processador',
  nome_impresso           VARCHAR(26) NOT NULL,
  validade                CHAR(5)     NOT NULL COMMENT 'MM/AA',
  dia_vencimento_fatura   INT         NULL,
  aproximacao_ativa       BOOLEAN     NOT NULL DEFAULT TRUE,
  compras_internacionais  BOOLEAN     NOT NULL DEFAULT FALSE,
  status                  ENUM('solicitado','em_transporte','ativo','bloqueado_temporario','cancelado') NOT NULL DEFAULT 'solicitado',
  emitido_em              DATETIME    NULL,
  criado_em               DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em           DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_cartoes_token (token_processador),
  CONSTRAINT chk_cartoes_dia_venc CHECK (dia_vencimento_fatura BETWEEN 1 AND 28),
  CONSTRAINT fk_cartoes_conta FOREIGN KEY (conta_id) REFERENCES contas(id)
) ENGINE=InnoDB;

CREATE TABLE compras_cartao (
  id                CHAR(36)      NOT NULL DEFAULT (UUID()),
  cartao_id         CHAR(36)      NOT NULL,
  estabelecimento   VARCHAR(150)  NOT NULL,
  mcc               CHAR(4)       NULL COMMENT 'Código do ramo do comércio',
  categoria_id      CHAR(36)      NULL,
  valor_total       DECIMAL(15,2) NOT NULL,
  num_parcelas      INT           NOT NULL DEFAULT 1,
  funcao_usada      ENUM('debito','credito') NOT NULL,
  status            ENUM('autorizada','negada','cancelada','estornada') NOT NULL,
  motivo_negativa   VARCHAR(100)  NULL,
  realizada_em      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  criado_em         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT chk_compras_parcelas CHECK (num_parcelas >= 1),
  CONSTRAINT fk_compras_cartao    FOREIGN KEY (cartao_id)    REFERENCES cartoes(id),
  CONSTRAINT fk_compras_categoria FOREIGN KEY (categoria_id) REFERENCES categorias(id)
) ENGINE=InnoDB;

CREATE TABLE faturas (
  id               CHAR(36)      NOT NULL DEFAULT (UUID()),
  cliente_id       CHAR(36)      NOT NULL,
  mes_referencia   CHAR(7)       NOT NULL COMMENT 'AAAA-MM',
  data_fechamento  DATE          NOT NULL,
  data_vencimento  DATE          NOT NULL,
  valor_total      DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  valor_minimo     DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  valor_pago       DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  pago_em          DATETIME      NULL,
  status           ENUM('aberta','fechada','paga','paga_parcial','atrasada') NOT NULL DEFAULT 'aberta',
  dias_atraso      INT           NOT NULL DEFAULT 0,
  criado_em        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_faturas_cliente_mes (cliente_id, mes_referencia),
  CONSTRAINT fk_faturas_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

CREATE TABLE lancamentos_fatura (
  id              CHAR(36)      NOT NULL DEFAULT (UUID()),
  fatura_id       CHAR(36)      NOT NULL,
  compra_id       CHAR(36)      NULL COMMENT 'Vazio para juros e tarifas',
  tipo            ENUM('compra','parcela','juros','multa','tarifa','estorno','pagamento') NOT NULL,
  numero_parcela  INT           NULL,
  valor           DECIMAL(15,2) NOT NULL,
  descricao       VARCHAR(150)  NULL,
  criado_em       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_lancamentos_fatura FOREIGN KEY (fatura_id) REFERENCES faturas(id),
  CONSTRAINT fk_lancamentos_compra FOREIGN KEY (compra_id) REFERENCES compras_cartao(id)
) ENGINE=InnoDB;

-- =====================================================================
-- MÓDULO 4 - ANÁLISE DE PERFIL E CRÉDITO PROGRESSIVO
-- =====================================================================

CREATE TABLE eventos_comportamentais (
  id             CHAR(36)      NOT NULL DEFAULT (UUID()),
  cliente_id     CHAR(36)      NOT NULL,
  tipo_evento    ENUM('fatura_paga_em_dia','fatura_atrasada','deposito_recebido','salario_recebido','compra_realizada','acesso_app','meta_atingida','open_finance_conectado','parcela_paga','saldo_negativo') NOT NULL,
  origem         ENUM('conta','cartao','emprestimo','open_finance','app') NOT NULL,
  referencia_id  CHAR(36)      NULL COMMENT 'Id do registro que gerou o evento',
  valor          DECIMAL(15,2) NULL,
  impacto        ENUM('positivo','neutro','negativo') NOT NULL,
  dados_extras   JSON          NULL,
  ocorrido_em    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  criado_em      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_eventos_cliente_data (cliente_id, ocorrido_em),
  CONSTRAINT fk_eventos_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

CREATE TABLE perfil_financeiro (
  id                       CHAR(36)      NOT NULL DEFAULT (UUID()),
  cliente_id               CHAR(36)      NOT NULL,
  renda_media_comprovada   DECIMAL(15,2) NULL,
  gasto_medio_mensal       DECIMAL(15,2) NULL,
  comprometimento_renda    DECIMAL(5,2)  NULL COMMENT '% da renda usada em dívidas',
  faturas_pagas_em_dia     INT           NOT NULL DEFAULT 0,
  faturas_atrasadas        INT           NOT NULL DEFAULT 0,
  maior_atraso_dias        INT           NOT NULL DEFAULT 0,
  meses_de_relacionamento  INT           NOT NULL DEFAULT 0,
  frequencia_uso_app       INT           NOT NULL DEFAULT 0 COMMENT 'Acessos nos últimos 30 dias',
  tem_open_finance         BOOLEAN       NOT NULL DEFAULT FALSE,
  saldo_medio              DECIMAL(15,2) NULL,
  perfil_risco             ENUM('muito_baixo','baixo','medio','alto','muito_alto') NULL,
  criado_em                DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_perfil_cliente (cliente_id),
  CONSTRAINT fk_perfil_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

CREATE TABLE scores_credito (
  id                 CHAR(36)    NOT NULL DEFAULT (UUID()),
  cliente_id         CHAR(36)    NOT NULL,
  score_interno      INT         NOT NULL,
  score_bureau       INT         NULL,
  versao_modelo      VARCHAR(20) NOT NULL,
  fatores_positivos  JSON        NULL,
  fatores_negativos  JSON        NULL,
  calculado_em       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  criado_em          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_scores_cliente_data (cliente_id, calculado_em),
  CONSTRAINT chk_scores_interno CHECK (score_interno BETWEEN 0 AND 1000),
  CONSTRAINT fk_scores_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

CREATE TABLE regras_progressao_credito (
  id                      CHAR(36)      NOT NULL DEFAULT (UUID()),
  nome                    VARCHAR(100)  NOT NULL,
  score_minimo            INT           NOT NULL DEFAULT 0,
  faturas_em_dia_minimas  INT           NOT NULL DEFAULT 0,
  meses_minimos           INT           NOT NULL DEFAULT 0,
  percentual_aumento      DECIMAL(5,2)  NOT NULL,
  limite_maximo           DECIMAL(15,2) NOT NULL,
  ativa                   BOOLEAN       NOT NULL DEFAULT TRUE,
  criado_em               DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE limites_credito (
  id                              CHAR(36)      NOT NULL DEFAULT (UUID()),
  cliente_id                      CHAR(36)      NOT NULL,
  limite_total                    DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  limite_utilizado                DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  limite_disponivel               DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  limite_emprestimo_pre_aprovado  DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  proximo_limite_previsto         DECIMAL(15,2) NULL,
  proxima_revisao_em              DATE          NULL,
  criado_em                       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em                   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_limites_cliente (cliente_id),
  CONSTRAINT fk_limites_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

CREATE TABLE historico_limite (
  id               CHAR(36)      NOT NULL DEFAULT (UUID()),
  cliente_id       CHAR(36)      NOT NULL,
  limite_anterior  DECIMAL(15,2) NOT NULL,
  limite_novo      DECIMAL(15,2) NOT NULL,
  motivo           ENUM('aumento_automatico','solicitacao_cliente','reducao_risco','subida_nivel','open_finance') NOT NULL,
  score_id         CHAR(36)      NULL,
  regra_id         CHAR(36)      NULL,
  alterado_em      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  criado_em        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_histlimite_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id),
  CONSTRAINT fk_histlimite_score   FOREIGN KEY (score_id)   REFERENCES scores_credito(id),
  CONSTRAINT fk_histlimite_regra   FOREIGN KEY (regra_id)   REFERENCES regras_progressao_credito(id)
) ENGINE=InnoDB;

-- =====================================================================
-- MÓDULO 5 - EMPRÉSTIMO PERSONALIZADO
-- =====================================================================

CREATE TABLE propostas_emprestimo (
  id                 CHAR(36)      NOT NULL DEFAULT (UUID()),
  cliente_id         CHAR(36)      NOT NULL,
  score_id           CHAR(36)      NULL,
  valor_solicitado   DECIMAL(15,2) NOT NULL,
  valor_aprovado     DECIMAL(15,2) NULL,
  num_parcelas       INT           NOT NULL,
  taxa_juros_mensal  DECIMAL(5,2)  NULL COMMENT '% ao mês',
  cet_anual          DECIMAL(6,2)  NULL COMMENT 'Custo efetivo total',
  valor_parcela      DECIMAL(15,2) NULL,
  finalidade         VARCHAR(100)  NULL,
  status             ENUM('simulada','enviada','aprovada','recusada','expirada','contratada') NOT NULL DEFAULT 'simulada',
  validade_ate       DATETIME      NULL,
  criado_em          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_propostas_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id),
  CONSTRAINT fk_propostas_score   FOREIGN KEY (score_id)   REFERENCES scores_credito(id)
) ENGINE=InnoDB;

CREATE TABLE contratos_emprestimo (
  id                     CHAR(36)      NOT NULL DEFAULT (UUID()),
  proposta_id            CHAR(36)      NOT NULL,
  cliente_id             CHAR(36)      NOT NULL,
  conta_id               CHAR(36)      NOT NULL,
  numero_contrato        VARCHAR(20)   NOT NULL,
  valor_contratado       DECIMAL(15,2) NOT NULL,
  saldo_devedor          DECIMAL(15,2) NOT NULL,
  data_primeira_parcela  DATE          NOT NULL,
  status                 ENUM('ativo','quitado','em_atraso','renegociado','cancelado') NOT NULL DEFAULT 'ativo',
  assinado_em            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  quitado_em             DATETIME      NULL,
  criado_em              DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_contratos_numero (numero_contrato),
  UNIQUE KEY uk_contratos_proposta (proposta_id),
  CONSTRAINT fk_contratos_proposta FOREIGN KEY (proposta_id) REFERENCES propostas_emprestimo(id),
  CONSTRAINT fk_contratos_cliente  FOREIGN KEY (cliente_id)  REFERENCES clientes(id),
  CONSTRAINT fk_contratos_conta    FOREIGN KEY (conta_id)    REFERENCES contas(id)
) ENGINE=InnoDB;

CREATE TABLE parcelas_emprestimo (
  id              CHAR(36)      NOT NULL DEFAULT (UUID()),
  contrato_id     CHAR(36)      NOT NULL,
  numero_parcela  INT           NOT NULL,
  valor           DECIMAL(15,2) NOT NULL,
  vencimento      DATE          NOT NULL,
  valor_pago      DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  pago_em         DATETIME      NULL,
  juros_atraso    DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  status          ENUM('a_vencer','paga','paga_atrasada','vencida') NOT NULL DEFAULT 'a_vencer',
  transacao_id    CHAR(36)      NULL,
  criado_em       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_parcelas_contrato_num (contrato_id, numero_parcela),
  CONSTRAINT fk_parcelas_contrato  FOREIGN KEY (contrato_id)  REFERENCES contratos_emprestimo(id),
  CONSTRAINT fk_parcelas_transacao FOREIGN KEY (transacao_id) REFERENCES transacoes(id)
) ENGINE=InnoDB;

-- =====================================================================
-- MÓDULO 6 - OPEN FINANCE
-- =====================================================================

CREATE TABLE instituicoes_financeiras (
  id                      CHAR(36)     NOT NULL DEFAULT (UUID()),
  nome                    VARCHAR(100) NOT NULL,
  codigo_banco            CHAR(3)      NULL COMMENT 'Código COMPE',
  cnpj                    CHAR(14)     NOT NULL,
  participa_open_finance  BOOLEAN      NOT NULL DEFAULT TRUE,
  url_logo                VARCHAR(255) NULL,
  criado_em               DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_instituicoes_cnpj (cnpj)
) ENGINE=InnoDB;

CREATE TABLE consentimentos_open_finance (
  id                        CHAR(36)     NOT NULL DEFAULT (UUID()),
  cliente_id                CHAR(36)     NOT NULL,
  instituicao_id            CHAR(36)     NOT NULL,
  id_consentimento_externo  VARCHAR(100) NULL,
  permissoes                JSON         NULL,
  status                    ENUM('aguardando_autorizacao','autorizado','rejeitado','revogado','expirado') NOT NULL DEFAULT 'aguardando_autorizacao',
  autorizado_em             DATETIME     NULL,
  expira_em                 DATETIME     NULL COMMENT 'Prazo máximo de 12 meses',
  revogado_em               DATETIME     NULL,
  ultima_sincronizacao_em   DATETIME     NULL,
  criado_em                 DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_consentof_cliente     FOREIGN KEY (cliente_id)     REFERENCES clientes(id),
  CONSTRAINT fk_consentof_instituicao FOREIGN KEY (instituicao_id) REFERENCES instituicoes_financeiras(id)
) ENGINE=InnoDB;

CREATE TABLE contas_externas (
  id                     CHAR(36)      NOT NULL DEFAULT (UUID()),
  consentimento_id       CHAR(36)      NOT NULL,
  tipo_produto           ENUM('conta_corrente','poupanca','cartao_credito','emprestimo','financiamento') NOT NULL,
  identificador_externo  VARCHAR(100)  NOT NULL,
  saldo                  DECIMAL(15,2) NULL,
  limite                 DECIMAL(15,2) NULL,
  saldo_devedor          DECIMAL(15,2) NULL,
  criado_em              DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_contasext_consent FOREIGN KEY (consentimento_id) REFERENCES consentimentos_open_finance(id)
) ENGINE=InnoDB;

CREATE TABLE transacoes_externas (
  id                   CHAR(36)      NOT NULL DEFAULT (UUID()),
  conta_externa_id     CHAR(36)      NOT NULL,
  id_externo           VARCHAR(100)  NOT NULL,
  tipo                 VARCHAR(50)   NULL,
  direcao              ENUM('entrada','saida') NOT NULL,
  valor                DECIMAL(15,2) NOT NULL,
  descricao            VARCHAR(150)  NULL,
  categoria_id         CHAR(36)      NULL,
  eh_renda_recorrente  BOOLEAN       NOT NULL DEFAULT FALSE,
  realizada_em         DATETIME      NOT NULL,
  criado_em            DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_transext_conta_idext (conta_externa_id, id_externo),
  CONSTRAINT fk_transext_conta     FOREIGN KEY (conta_externa_id) REFERENCES contas_externas(id),
  CONSTRAINT fk_transext_categoria FOREIGN KEY (categoria_id)     REFERENCES categorias(id)
) ENGINE=InnoDB;

-- =====================================================================
-- MÓDULO 7 - GAMIFICAÇÃO
-- =====================================================================

CREATE TABLE niveis (
  id                    CHAR(36)     NOT NULL DEFAULT (UUID()),
  ordem                 INT          NOT NULL,
  nome                  VARCHAR(50)  NOT NULL,
  xp_minimo             INT          NOT NULL,
  multiplicador_pontos  DECIMAL(4,2) NOT NULL DEFAULT 1.00,
  cor_hex               CHAR(7)      NULL,
  url_icone             VARCHAR(255) NULL,
  criado_em             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_niveis_ordem (ordem)
) ENGINE=InnoDB;

CREATE TABLE parceiros (
  id               CHAR(36)     NOT NULL DEFAULT (UUID()),
  nome             VARCHAR(100) NOT NULL,
  tipo             ENUM('companhia_aerea','sala_vip','varejo','programa_fidelidade') NOT NULL,
  taxa_conversao   DECIMAL(6,2) NULL COMMENT 'Pontos para 1 milha do parceiro',
  ativo            BOOLEAN      NOT NULL DEFAULT TRUE,
  criado_em        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE beneficios (
  id               CHAR(36)      NOT NULL DEFAULT (UUID()),
  nome             VARCHAR(100)  NOT NULL,
  tipo             ENUM('sala_vip','multiplicador','cashback','isencao_tarifa','aumento_limite','desconto_parceiro') NOT NULL,
  parceiro_id      CHAR(36)      NULL,
  nivel_minimo_id  CHAR(36)      NULL,
  usos_por_mes     INT           NULL,
  valor            DECIMAL(10,2) NULL,
  ativo            BOOLEAN       NOT NULL DEFAULT TRUE,
  criado_em        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_beneficios_parceiro FOREIGN KEY (parceiro_id)     REFERENCES parceiros(id),
  CONSTRAINT fk_beneficios_nivel    FOREIGN KEY (nivel_minimo_id) REFERENCES niveis(id)
) ENGINE=InnoDB;

CREATE TABLE conquistas (
  id                    CHAR(36)     NOT NULL DEFAULT (UUID()),
  codigo                VARCHAR(50)  NOT NULL,
  nome                  VARCHAR(100) NOT NULL,
  descricao             VARCHAR(255) NULL,
  categoria             ENUM('pagamento','uso','credito','viagem','educacao_financeira') NOT NULL,
  criterio_tipo_evento  ENUM('fatura_paga_em_dia','fatura_atrasada','deposito_recebido','salario_recebido','compra_realizada','acesso_app','meta_atingida','open_finance_conectado','parcela_paga','saldo_negativo') NULL,
  criterio_quantidade   INT          NOT NULL DEFAULT 1,
  nivel_minimo_id       CHAR(36)     NULL,
  xp_recompensa         INT          NOT NULL DEFAULT 0,
  pontos_recompensa     INT          NOT NULL DEFAULT 0,
  beneficio_id          CHAR(36)     NULL,
  url_icone             VARCHAR(255) NULL,
  ativa                 BOOLEAN      NOT NULL DEFAULT TRUE,
  criado_em             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_conquistas_codigo (codigo),
  CONSTRAINT fk_conquistas_nivel     FOREIGN KEY (nivel_minimo_id) REFERENCES niveis(id),
  CONSTRAINT fk_conquistas_beneficio FOREIGN KEY (beneficio_id)    REFERENCES beneficios(id)
) ENGINE=InnoDB;

CREATE TABLE progresso_cliente (
  id                      CHAR(36) NOT NULL DEFAULT (UUID()),
  cliente_id              CHAR(36) NOT NULL,
  nivel_id                CHAR(36) NOT NULL,
  xp_total                INT      NOT NULL DEFAULT 0,
  xp_para_proximo_nivel   INT      NOT NULL DEFAULT 0,
  saldo_pontos            INT      NOT NULL DEFAULT 0,
  saldo_milhas            INT      NOT NULL DEFAULT 0,
  sequencia_dias_ativos   INT      NOT NULL DEFAULT 0,
  proxima_conquista_id    CHAR(36) NULL,
  subiu_nivel_em          DATETIME NULL,
  criado_em               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_progresso_cliente (cliente_id),
  CONSTRAINT fk_progresso_cliente   FOREIGN KEY (cliente_id)           REFERENCES clientes(id),
  CONSTRAINT fk_progresso_nivel     FOREIGN KEY (nivel_id)             REFERENCES niveis(id),
  CONSTRAINT fk_progresso_conquista FOREIGN KEY (proxima_conquista_id) REFERENCES conquistas(id)
) ENGINE=InnoDB;

CREATE TABLE regras_pontuacao (
  id               CHAR(36)     NOT NULL DEFAULT (UUID()),
  tipo_evento      ENUM('fatura_paga_em_dia','fatura_atrasada','deposito_recebido','salario_recebido','compra_realizada','acesso_app','meta_atingida','open_finance_conectado','parcela_paga','saldo_negativo') NOT NULL,
  xp_ganho         INT          NOT NULL DEFAULT 0,
  pontos_ganhos    INT          NOT NULL DEFAULT 0,
  milhas_ganhas    INT          NOT NULL DEFAULT 0,
  pontos_por_real  DECIMAL(6,2) NULL,
  limite_diario    INT          NULL COMMENT 'Evita abuso',
  ativa            BOOLEAN      NOT NULL DEFAULT TRUE,
  valida_de        DATE         NULL,
  valida_ate       DATE         NULL,
  criado_em        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE resgates (
  id                 CHAR(36)      NOT NULL DEFAULT (UUID()),
  cliente_id         CHAR(36)      NOT NULL,
  tipo               ENUM('transferencia_milhas','cashback','produto','desconto_fatura') NOT NULL,
  parceiro_id        CHAR(36)      NULL,
  moeda_usada        ENUM('pontos','milhas') NOT NULL,
  quantidade_usada   INT           NOT NULL,
  valor_equivalente  DECIMAL(15,2) NULL COMMENT 'Em reais',
  status             ENUM('solicitado','processando','concluido','falhou') NOT NULL DEFAULT 'solicitado',
  solicitado_em      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  concluido_em       DATETIME      NULL,
  criado_em          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_resgates_cliente  FOREIGN KEY (cliente_id)  REFERENCES clientes(id),
  CONSTRAINT fk_resgates_parceiro FOREIGN KEY (parceiro_id) REFERENCES parceiros(id)
) ENGINE=InnoDB;

CREATE TABLE movimentacoes_recompensa (
  id             CHAR(36)     NOT NULL DEFAULT (UUID()),
  cliente_id     CHAR(36)     NOT NULL,
  moeda          ENUM('xp','pontos','milhas') NOT NULL,
  tipo           ENUM('credito','debito','expiracao','estorno') NOT NULL,
  quantidade     INT          NOT NULL,
  saldo_apos     INT          NOT NULL,
  evento_id      CHAR(36)     NULL,
  regra_id       CHAR(36)     NULL,
  resgate_id     CHAR(36)     NULL,
  descricao      VARCHAR(150) NULL,
  expira_em      DATE         NULL,
  ocorrido_em    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  criado_em      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_movrec_cliente_data (cliente_id, ocorrido_em),
  CONSTRAINT fk_movrec_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id),
  CONSTRAINT fk_movrec_evento  FOREIGN KEY (evento_id)  REFERENCES eventos_comportamentais(id),
  CONSTRAINT fk_movrec_regra   FOREIGN KEY (regra_id)   REFERENCES regras_pontuacao(id),
  CONSTRAINT fk_movrec_resgate FOREIGN KEY (resgate_id) REFERENCES resgates(id)
) ENGINE=InnoDB;

CREATE TABLE conquistas_cliente (
  id               CHAR(36) NOT NULL DEFAULT (UUID()),
  cliente_id       CHAR(36) NOT NULL,
  conquista_id     CHAR(36) NOT NULL,
  progresso_atual  INT      NOT NULL DEFAULT 0,
  status           ENUM('bloqueada','em_andamento','conquistada') NOT NULL DEFAULT 'bloqueada',
  conquistada_em   DATETIME NULL,
  visualizada      BOOLEAN  NOT NULL DEFAULT FALSE,
  criado_em        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_conqcli_cliente_conquista (cliente_id, conquista_id),
  CONSTRAINT fk_conqcli_cliente   FOREIGN KEY (cliente_id)   REFERENCES clientes(id),
  CONSTRAINT fk_conqcli_conquista FOREIGN KEY (conquista_id) REFERENCES conquistas(id)
) ENGINE=InnoDB;

CREATE TABLE beneficios_cliente (
  id               CHAR(36)    NOT NULL DEFAULT (UUID()),
  cliente_id       CHAR(36)    NOT NULL,
  beneficio_id     CHAR(36)    NOT NULL,
  origem           ENUM('nivel','conquista','campanha') NOT NULL,
  status           ENUM('liberado','utilizado','expirado') NOT NULL DEFAULT 'liberado',
  usos_restantes   INT         NULL,
  codigo_voucher   VARCHAR(50) NULL,
  liberado_em      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expira_em        DATETIME    NULL,
  criado_em        DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_benefcli_cliente   FOREIGN KEY (cliente_id)   REFERENCES clientes(id),
  CONSTRAINT fk_benefcli_beneficio FOREIGN KEY (beneficio_id) REFERENCES beneficios(id)
) ENGINE=InnoDB;

-- =====================================================================
-- MÓDULO 8 - GESTÃO FINANCEIRA (categorias já foi criada acima)
-- =====================================================================

CREATE TABLE orcamentos (
  id                 CHAR(36)      NOT NULL DEFAULT (UUID()),
  cliente_id         CHAR(36)      NOT NULL,
  categoria_id       CHAR(36)      NOT NULL,
  mes_referencia     CHAR(7)       NOT NULL COMMENT 'AAAA-MM',
  valor_planejado    DECIMAL(15,2) NOT NULL,
  valor_gasto        DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  alerta_percentual  INT           NOT NULL DEFAULT 80,
  status             ENUM('dentro','alerta','estourado') NOT NULL DEFAULT 'dentro',
  criado_em          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_orcamentos_cli_cat_mes (cliente_id, categoria_id, mes_referencia),
  CONSTRAINT fk_orcamentos_cliente   FOREIGN KEY (cliente_id)   REFERENCES clientes(id),
  CONSTRAINT fk_orcamentos_categoria FOREIGN KEY (categoria_id) REFERENCES categorias(id)
) ENGINE=InnoDB;

CREATE TABLE metas_financeiras (
  id                 CHAR(36)      NOT NULL DEFAULT (UUID()),
  cliente_id         CHAR(36)      NOT NULL,
  nome               VARCHAR(100)  NOT NULL,
  valor_alvo         DECIMAL(15,2) NOT NULL,
  valor_atual        DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  data_alvo          DATE          NULL,
  aporte_automatico  DECIMAL(15,2) NULL,
  status             ENUM('ativa','concluida','cancelada') NOT NULL DEFAULT 'ativa',
  concluida_em       DATETIME      NULL,
  criado_em          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_metas_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

-- =====================================================================
-- MÓDULO 9 - SEGURANÇA, NOTIFICAÇÕES E AUDITORIA
-- =====================================================================

CREATE TABLE dispositivos (
  id                         CHAR(36)     NOT NULL DEFAULT (UUID()),
  cliente_id                 CHAR(36)     NOT NULL,
  identificador_dispositivo  VARCHAR(100) NOT NULL,
  modelo                     VARCHAR(100) NULL,
  sistema_operacional        VARCHAR(50)  NULL,
  token_push                 VARCHAR(255) NULL,
  confiavel                  BOOLEAN      NOT NULL DEFAULT FALSE,
  biometria_ativa            BOOLEAN      NOT NULL DEFAULT FALSE,
  ultimo_acesso_em           DATETIME     NULL,
  criado_em                  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em              DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_dispositivos_cli_ident (cliente_id, identificador_dispositivo),
  CONSTRAINT fk_dispositivos_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

CREATE TABLE sessoes_acesso (
  id                      CHAR(36)     NOT NULL DEFAULT (UUID()),
  cliente_id              CHAR(36)     NOT NULL,
  dispositivo_id          CHAR(36)     NULL,
  ip                      VARCHAR(45)  NULL,
  localizacao_aproximada  VARCHAR(100) NULL,
  metodo_login            ENUM('senha','biometria','token') NOT NULL,
  sucesso                 BOOLEAN      NOT NULL,
  iniciada_em             DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  encerrada_em            DATETIME     NULL,
  criado_em               DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_sessoes_cliente     FOREIGN KEY (cliente_id)     REFERENCES clientes(id),
  CONSTRAINT fk_sessoes_dispositivo FOREIGN KEY (dispositivo_id) REFERENCES dispositivos(id)
) ENGINE=InnoDB;

CREATE TABLE notificacoes (
  id             CHAR(36)     NOT NULL DEFAULT (UUID()),
  cliente_id     CHAR(36)     NOT NULL,
  tipo           ENUM('transacao','fatura','limite','conquista','nivel','seguranca','promocao') NOT NULL,
  canal          ENUM('push','email','sms','app') NOT NULL,
  titulo         VARCHAR(100) NOT NULL,
  mensagem       VARCHAR(500) NOT NULL,
  referencia_id  CHAR(36)     NULL COMMENT 'Registro ligado (conquista, fatura etc.)',
  lida           BOOLEAN      NOT NULL DEFAULT FALSE,
  enviada_em     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  lida_em        DATETIME     NULL,
  criado_em      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_notificacoes_cliente_lida (cliente_id, lida),
  CONSTRAINT fk_notificacoes_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

CREATE TABLE logs_auditoria (
  id              CHAR(36)    NOT NULL DEFAULT (UUID()),
  ator_tipo       ENUM('cliente','funcionario','sistema') NOT NULL,
  ator_id         CHAR(36)    NULL,
  acao            VARCHAR(50) NOT NULL,
  tabela_afetada  VARCHAR(50) NULL,
  registro_id     CHAR(36)    NULL,
  valores_antes   JSON        NULL,
  valores_depois  JSON        NULL,
  ip              VARCHAR(45) NULL,
  ocorrido_em     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  criado_em       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_logs_tabela_registro (tabela_afetada, registro_id)
) ENGINE=InnoDB;

-- =====================================================================
-- Conferência: deve listar 43 tabelas
-- =====================================================================
SHOW TABLES;
