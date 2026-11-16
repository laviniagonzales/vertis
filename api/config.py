"""
CONFIGURAÇÕES DA API VÉRTIS
===========================
Edite os valores abaixo de acordo com o MySQL instalado na sua máquina.
(Também dá para passar por variável de ambiente, sem mexer no arquivo.)
"""
import os

# --- Conexão com o MySQL -------------------------------------------------
DB_HOST = os.environ.get("VERTIS_DB_HOST", "localhost")
DB_PORTA = int(os.environ.get("VERTIS_DB_PORTA", "3306"))
DB_USUARIO = os.environ.get("VERTIS_DB_USUARIO", "root")
DB_SENHA = os.environ.get("VERTIS_DB_SENHA", "vertis123")   # <-- troque pela sua senha
DB_NOME = os.environ.get("VERTIS_DB_NOME", "vertis")

# --- Segurança -----------------------------------------------------------
# Chave usada para "assinar" os tokens de login. Em produção seria secreta.
CHAVE_TOKEN = os.environ.get("VERTIS_CHAVE_TOKEN", "troque-esta-chave-no-projeto-real")
HORAS_VALIDADE_TOKEN = 12

# --- Parâmetros do negócio que não ficam no banco ------------------------
VERSAO_MODELO_SCORE = "v2.0"
DIA_VENCIMENTO_PADRAO = 10          # dia do mês em que a fatura vence
DIAS_ANTES_FECHAMENTO = 7           # a fatura fecha 7 dias antes do vencimento
PONTOS_POR_REAL_CASHBACK = 100      # 100 pontos = R$ 1,00
