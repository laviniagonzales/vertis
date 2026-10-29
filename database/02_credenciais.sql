-- =====================================================================
-- VÉRTIS - Tabela extra: credenciais (login do app)
--
-- POR QUE ESTA TABELA EXISTE?
-- O script original não tem onde guardar a senha do cliente.
-- Na apresentação (slide de cardinalidade) o grupo já previa uma
-- tabela "Autenticacao" (Cliente 1:N Autenticacao). Esta é ela.
--
-- A senha NUNCA é guardada como texto: guardamos só o "hash"
-- (uma impressão digital da senha, que não pode ser revertida),
-- como o próprio roteiro do banco exige no módulo 9.
-- =====================================================================

SET NAMES utf8mb4;
USE vertis;

CREATE TABLE IF NOT EXISTS credenciais (
  id                 CHAR(36)     NOT NULL DEFAULT (UUID()),
  cliente_id         CHAR(36)     NOT NULL,
  senha_hash         VARCHAR(255) NOT NULL COMMENT 'pbkdf2_sha256$iteracoes$sal$hash',
  tentativas_falhas  INT          NOT NULL DEFAULT 0,
  bloqueada_ate      DATETIME     NULL,
  criado_em          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_credenciais_cliente (cliente_id),
  CONSTRAINT fk_credenciais_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;
