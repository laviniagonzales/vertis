# VÉRTIS — Guia do projeto

> Crédito progressivo + gamificação para quem tem pouco ou nenhum histórico financeiro.
> Projeto Final de Computação Gráfica (UNASP-SP). Tudo em Python.

---

## 1. Como o sistema funciona (visão geral)

```
 📱 APP (Kivy, Python)         🔌 API (FastAPI, Python)         🗄️ BANCO (MySQL 8)
 ┌───────────────────┐  HTTP   ┌──────────────────────┐   SQL   ┌──────────────────┐
 │ telas + gráficos  │ ──────▶ │ regras de negócio:   │ ──────▶ │ 43 tabelas do    │
 │ (computação       │  JSON   │ score, limite, XP,   │         │ grupo + tabela   │
 │  gráfica)         │ ◀────── │ pontos, conquistas   │ ◀────── │ "credenciais"    │
 └───────────────────┘         └──────────────────────┘         └──────────────────┘
   roda no celular                roda no notebook                roda no notebook
```

**Por que existe a API no meio?** Um app de celular não deve falar direto com o banco:
a senha do MySQL ficaria dentro do app, e qualquer pessoa poderia extraí-la.
A API guarda a senha, confere quem está pedindo (token de login) e aplica as regras.

### O coração da Vértis: as duas trilhas

Toda ação do cliente vira um **evento** (`eventos_comportamentais`) que segue por duas trilhas:

| Trilha 1 — CRÉDITO | Trilha 2 — GAMIFICAÇÃO |
|---|---|
| evento → `perfil_financeiro` → `scores_credito` → `regras_progressao_credito` → `limites_credito` (+ `historico_limite`) | evento → `regras_pontuacao` → XP, pontos, milhas (`movimentacoes_recompensa`) → `niveis` → `conquistas` → `beneficios` |
| Arquivo: `api/servicos/credito.py` | Arquivo: `api/servicos/gamificacao.py` |

O ponto de encontro é `api/servicos/eventos.py`, a função `registrar()`.

---

## 2. Estrutura das pastas

```
vertis/
├── database/
│   ├── vertis_schema.sql          ← o script de vocês (só ganhou "SET NAMES utf8mb4" para os acentos)
│   ├── 02_credenciais.sql     ← tabela NOVA para a senha (ver seção 7)
│   └── 03_dados_iniciais.sql  ← níveis, regras, conquistas, categorias... (PROPOSTA para ajustar)
├── api/
│   ├── main.py                ← todas as rotas (endereços) da API
│   ├── config.py              ← ⚠️ coloque aqui a senha do SEU MySQL
│   ├── db.py                  ← conexão com o MySQL (SQL puro, com PyMySQL)
│   ├── relogio.py             ← relógio da simulação (para "avançar meses" na apresentação)
│   └── servicos/              ← regras de negócio, um arquivo por módulo do banco
│       ├── eventos.py         ← o ponto de encontro das duas trilhas
│       ├── credito.py         ← perfil, score 0–1000, revisão do limite
│       ├── gamificacao.py     ← XP, pontos, milhas, níveis, conquistas, resgates
│       ├── clientes.py        ← cadastro, login, resumo da tela inicial
│       ├── conta.py, cartao.py, emprestimo.py, open_finance.py, metas.py
│       ├── seguranca.py       ← hash de senha, token, validação de CPF
│       └── simulacao.py       ← modo demonstração (cliente Gabriel + "simular 1 mês")
└── app/
    ├── main.py                ← abre o app
    ├── servidor.py            ← conversa com a API
    ├── buildozer.spec         ← configuração para gerar o APK Android
    ├── cg/                    ← ⭐ COMPUTAÇÃO GRÁFICA (conteúdo da disciplina)
    │   ├── transformacoes.py  ← matrizes 2D/3D, coordenadas homogêneas, projeção
    │   ├── recorte.py         ← Cohen–Sutherland
    │   ├── raster.py          ← rasterização, antialiasing, Bézier, degradês, Phong
    │   ├── cartao3d.py        ← cartão 3D: malha, culling, pintor, shading, textura
    │   └── widgets.py         ← trilha de ascensão, moeda 3D, anel, medalhas
    └── telas/                 ← uma tela por arquivo
```

---

## 3. Rodando no Windows (passo a passo)

### 3.1 Instalar o que precisa (uma vez só)

1. **Python 3.12**: baixe em python.org. Na instalação, **marque "Add Python to PATH"**.
2. **MySQL 8 + MySQL Workbench**: baixe o "MySQL Installer for Windows" em dev.mysql.com.
   Anote a senha do usuário `root` que você criar.
3. **VS Code** (opcional, mas recomendado).

### 3.2 Criar o banco

No **MySQL Workbench**: *File → Open SQL Script* e execute (raio ⚡), **nesta ordem**:

1. `database/vertis_schema.sql`
2. `database/02_credenciais.sql`
3. `database/03_dados_iniciais.sql`

Confira: `SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='vertis';` → **44**.

### 3.3 Rodar a API

1. Abra `api/config.py` e troque `vertis123` pela **sua** senha do MySQL.
2. No terminal (PowerShell), dentro da pasta `api`:

```powershell
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

3. Abra no navegador: **http://localhost:8000/docs**. É a documentação automática do FastAPI:
   dá para testar cada rota clicando em *Try it out*. (Ótimo para mostrar na apresentação!)

### 3.4 Rodar o app no computador

Em **outro** terminal, dentro da pasta `app`:

```powershell
pip install -r requirements.txt
python main.py
```

Abre uma janela no formato de celular. Clique em **"Cliente de demonstração (Gabriel)"**.

---

## 4. Usando no celular de verdade

1. Notebook e celular na **mesma rede Wi-Fi**.
2. Descubra o IP do notebook: no PowerShell, `ipconfig` → "Endereço IPv4" (ex.: `192.168.0.15`).
3. Libere a porta no firewall (PowerShell **como administrador**, uma vez só):
   ```powershell
   New-NetFirewallRule -DisplayName "Vertis API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
   ```
4. No app, na tela de login, toque em **"servidor"** (canto de baixo) e digite `192.168.0.15:8000`.

> 💡 **Plano B para o dia:** se a rede da faculdade bloquear, rode o app no notebook
> (`python main.py`) e projete. Também funciona com o **roteador do celular** (hotspot).

---

## 5. Gerar o APK Android (no Windows, usando WSL)

O Buildozer (que transforma o app Python em APK) só funciona em Linux. No Windows usamos o **WSL**
(um Linux dentro do Windows). Faça **uma semana antes** da apresentação: a primeira vez demora.

1. PowerShell **como administrador**: `wsl --install` → reinicie o PC → crie usuário e senha do Ubuntu.
2. No Ubuntu (WSL), instale as dependências:

```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv autoconf libtool \
    pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev
python3 -m venv ~/venv-buildozer && source ~/venv-buildozer/bin/activate
pip install buildozer cython==0.29.36 setuptools
```

3. Copie a pasta `app` para **dentro do Linux** (compilar em `/mnt/c/...` é muito lento):

```bash
cp -r /mnt/c/Users/SEU_USUARIO/caminho/vertis/app ~/vertis-app
cd ~/vertis-app
buildozer -v android debug
```

4. A primeira vez leva **de 30 a 60 minutos** (baixa o SDK/NDK do Android). As próximas, poucos minutos.
5. O APK fica em `~/vertis-app/bin/vertis-1.0-arm64-v8a-debug.apk`. Copie para o Windows
   (`cp bin/*.apk /mnt/c/Users/SEU_USUARIO/Desktop/`), mande para o celular e instale
   (o Android pede para permitir "instalar apps de fontes desconhecidas").

> Já está configurado no `buildozer.spec`: permissão de INTERNET e liberação de HTTP
> (`android_extra.xml`), necessária porque a API local usa `http://` e não `https://`.

---

## 6. Regras de negócio propostas (para o grupo ajustar)

Quase tudo fica **no banco** (`03_dados_iniciais.sql`), então dá para mudar **sem mexer no código**.

### 6.1 Limite inicial (código: `credito.py → limite_inicial`)
15% a 20% da renda declarada (formal = 20%; informal/autônomo/benefício = 15%), **entre R$ 200 e R$ 1.000**.
Ex.: Gabriel, R$ 2.500 informal → **R$ 350**.

### 6.2 Score interno 0–1000 (código: `credito.py → _pontuar`)
Modelo de **pontos**, fácil de explicar e transparente (o app mostra cada fator):

| Fator | Pontos |
|---|---|
| Ponto de partida (todo cliente) | **300** |
| Cada fatura paga em dia | +60 (máx. +300) |
| Cada fatura atrasada | −120 (máx. −360) |
| Maior atraso | −2 por dia (máx. −150) |
| Meses de relacionamento | +10 por mês (máx. +100) |
| Renda comprovada pela movimentação | +50 |
| Comprometimento da renda < 30% / 30–50% / > 50% | +100 / +40 / −80 |
| Open Finance conectado | +80 |
| Uso do app (15+ ou 5+ acessos/mês) | +40 / +20 |
| Mantém saldo ≥ 10% da renda | +50 |
| Cada parcela de empréstimo paga | +20 (máx. +100) |
| Cada vez com saldo negativo | −50 |

Perfil de risco: ≥800 muito baixo • ≥650 baixo • ≥500 médio • ≥350 alto • abaixo muito alto.

### 6.3 Progressão do limite (tabela `regras_progressao_credito`)
Quando uma fatura é paga **em dia**, o sistema escolhe a regra mais avançada que o cliente cumpre:

| Regra | Score mín. | Faturas em dia | Meses | Aumento | Teto |
|---|---|---|---|---|---|
| Primeira fatura em dia | 400 | 1 | 0 | +30% | R$ 1.500 |
| 3 faturas em dia | 500 | 3 | 3 | +50% | R$ 3.500 |
| 6 faturas em dia | 600 | 6 | 6 | +40% | R$ 6.000 |
| Cliente de confiança | 750 | 10 | 10 | +30% | R$ 15.000 |

Travas de segurança: o limite nunca passa de **2x a renda**; revisão no máximo a cada 25 dias;
**atraso reduz 20%** e adia a próxima revisão em 60 dias; Open Finance dá **+20% uma única vez**.

### 6.4 Gamificação
- **Níveis** (XP): Semente 0 • Broto 600 • Ascensão 1.500 • VIP Nacional 3.000 • VIP Internacional 5.500 • Vértice 9.000.
  Cada nível multiplica os pontos (1,0x → 2,0x).
- **Pontuação** (tabela `regras_pontuacao`): fatura em dia = 300 XP + 500 pts + 1.500 milhas;
  salário = 100 XP + 100 pts; compra = 5 XP + 1 pt por real; acesso diário = 10 XP (1x/dia)...
- **Conquistas** (10): Primeiro Passo, Fatura em Dia, Pagador Pontual (libera Multiplicador de Pontos),
  Fatura em Dia 6x, Salário na Vértis, Cliente Ativo, Open Finance Conectado, Primeira Meta,
  Crédito Responsável e **Nível VIP Nacional → libera a Sala VIP Aeroporto** (como no mockup).
- **Resgate**: 100 pontos = R$ 1,00 de cashback na conta.

### 6.5 Empréstimo (código: `emprestimo.py`)
Taxa pelo perfil de risco: 1,99% (muito baixo) • 2,99% • 3,99% • 5,49% (alto) • recusa (muito alto).
Parcela pela **Tabela Price**: `PMT = PV × i / (1 − (1+i)^−n)`. CET simplificado (sem IOF).
Pré-aprovado: até 1,5x a renda comprovada, proporcional ao score.

### Resultado da simulação (cliente Gabriel, pagando tudo em dia)

| Mês | Limite | Score | Nível |
|---|---|---|---|
| início | R$ 350 | 400 | Semente |
| 1 | R$ 450 | 610 | Broto |
| 2 | R$ 630 | 680 | Ascensão |
| 4 | R$ 1.210 | 820 | VIP Nacional (Sala VIP liberada) |
| 6 | R$ 2.710 | 900 | VIP Internacional |
| 8 | R$ 5.000 | 920 | (teto de 2x a renda) |

---

## 7. O que mudou em relação ao material do grupo

1. **Tabela nova `credenciais`** (`02_credenciais.sql`): o script original não tinha onde guardar a
   senha. O slide de cardinalidade já previa uma tabela "Autenticacao" — é ela. Guarda **só o hash** da senha.
2. **`SET NAMES utf8mb4`** no início dos scripts: sem isso, o MySQL do Windows pode gravar
   "Bônus" como "BÃ´nus".
3. **Nomes dos níveis** seguem o mockup (Ascensão, VIP Nacional...) em vez de Bronze/Prata/Ouro.
   Se preferirem os outros, basta mudar o `INSERT INTO niveis`.

## 8. O que é SIMULADO (e por quê)

Para a apresentação, algumas integrações externas são simuladas, mas o fluxo de dados é o real:
- **Pix**: entre clientes Vértis funciona de verdade (sai de uma conta, entra na outra); para outros bancos é simulado.
- **Open Finance**: o consentimento, a importação sem duplicar e a análise de renda são reais; os dados "do outro banco" são gerados.
- **Processador do cartão**: guardamos só os 4 últimos dígitos e um token, como no roteiro.
- **Tempo**: o "Simular 1 mês" avança o relógio da API (arquivo `api/relogio.json`).
  Para começar do zero: `POST /demo/resetar` (pelo /docs) — apaga os clientes e zera o relógio.

---

## 9. Onde está cada conteúdo da disciplina (para a apresentação)

| Conteúdo do plano de ensino | Onde aparece | Arquivo |
|---|---|---|
| Pontos, vetores, matrizes, coordenadas | Trilha de ascensão: cada mudança de limite vira um ponto; curva de Bézier com vetores tangentes | `cg/raster.py → curva_suave`, `cg/widgets.py` |
| Transformações 2D | Avatar (T·S), seta no fim da trilha (T·R·S), medalha que "explode" (escala animada) | `cg/transformacoes.py`, `cg/widgets.py`, `telas/componentes.py` |
| Transformações 3D | Cartão 3D (M = Rx·Ry) e moeda de pontos girando (Ry) | `cg/cartao3d.py`, `cg/widgets.py` |
| Recorte e visibilidade | Cohen–Sutherland na trilha e no Lab; back-face culling e algoritmo do pintor no cartão e na moeda | `cg/recorte.py`, `cg/cartao3d.py` |
| Transformações projetivas | Perspectiva com divisão por w = 1 − z/d | `cg/transformacoes.py → perspectiva/projetar` |
| Objetos e cenas 3D | Cartão como malha de faixas + laterais; moeda como dois discos | `cg/cartao3d.py` |
| Iluminação e tonalização (shading) | Phong por faixa no cartão; Phong por pixel nas medalhas; degradês interpolados | `cg/cartao3d.py → _sombrear`, `cg/raster.py → esfera_iluminada` |
| Texturas e mapeamento | Arte do cartão desenhada em Fbo e mapeada com coordenadas (u, v) | `cg/cartao3d.py → _criar_texturas` |
| Rasterização | Trilha, anel do crédito e medidor do score rasterizados pixel a pixel com NumPy; Bresenham no Lab | `cg/raster.py` |
| Antialiasing | Cobertura por distância (trilha/anel) e superamostragem 4x4 (Lab, com botão serrilhado × suave) | `cg/raster.py`, `telas/lab.py` |

A aba **Lab CG** do app foi feita para explicar ao vivo: grade de pixels ampliada,
recorte arrastando a linha, cartão em modo aramado com a matriz mudando, e luz de Phong com controle.

---

## 10. Roteiro sugerido para a demonstração (≈ 7 minutos)

| Tempo | Quem | O que mostrar |
|---|---|---|
| 0:00 | A | Banco no Workbench (44 tabelas) + API no ar (`/docs`) |
| 1:00 | B | App: **cadastro** de um cliente novo (renda informal, consentimentos LGPD) → limite inicial pequeno |
| 2:00 | B | Compra no cartão → a fatura aparece |
| 2:30 | C | Login do **Gabriel** → tela de Evolução. Clicar **"Simular 1 mês"** 3–4 vezes: o limite sobe, a trilha cresce, celebrações de nível e conquista, **Sala VIP liberada** |
| 4:00 | C | **Meu score**: os fatores que explicam a nota (transparência) → conectar **Open Finance** (+20% no limite) → simular **empréstimo** com taxa personalizada |
| 5:00 | D | Aba **Cartão**: girar o cartão 3D com o dedo, virar para o verso |
| 5:30 | D | Aba **Lab CG**: serrilhado × antialiasing, recorte, modo aramado + matriz, luz de Phong |
| 6:30 | todos | Fechamento: problema → solução → resultado |

---

## 11. Problemas comuns

| Sintoma | Solução |
|---|---|
| `Access denied for user 'root'` | Senha errada em `api/config.py` |
| `RuntimeError: 'cryptography' package is required` | `pip install cryptography` |
| App: "Não consegui falar com o servidor" | A API está rodando? O endereço em "servidor" está certo? Firewall liberado? |
| Acentos estranhos no banco | Rode de novo os scripts (eles têm `SET NAMES utf8mb4`) |
| Quero começar a demonstração do zero | Em `/docs`, rode `POST /demo/resetar` |
| Buildozer falha no meio | Rode `buildozer android clean` e tente de novo; confira se está dentro de `~/` e não em `/mnt/c` |
