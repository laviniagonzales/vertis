# Vértis – Roteiro do Banco de Dados

Oct 26, 2026 · @Lavínia Gonzales de Lima

## Visão geral

A Vértis precisa de 43 tabelas, organizadas em 9 módulos. Todos os módulos giram em torno da tabela `clientes`. O coração do propósito está em dois módulos: crédito progressivo e gamificação. Eles transformam o comportamento do cliente em limite, pontos, milhas e conquistas.

| Módulo | Tabelas | Para que serve |
| --- | --- | --- |
| Clientes e identidade | 4 | Cadastro, endereço, documentos (KYC) e consentimentos LGPD |
| Conta digital | 5 | Conta corrente, transações, Pix, boletos e favorecidos |
| Cartões | 4 | Cartões débito/crédito, compras, faturas e lançamentos |
| Análise de perfil e crédito progressivo | 6 | Eventos de comportamento, perfil, score e evolução do limite |
| Empréstimo personalizado | 3 | Propostas, contratos e parcelas |
| Open Finance | 4 | Instituições, consentimentos, contas e transações externas |
| Gamificação | 10 | Níveis, XP, pontos, milhas, conquistas, benefícios e resgates |
| Gestão financeira | 3 | Categorias, orçamentos e metas |
| Segurança e comunicação | 4 | Dispositivos, sessões, notificações e auditoria |

**Convenções para todas as tabelas**

- Nomes em minúsculas, com `_` entre palavras e no plural (ex.: `chaves_pix`).
- Chave primária `id` do tipo UUID em todas as tabelas. Chaves estrangeiras terminam em `_id`.
- Toda tabela tem `criado_em` e `atualizado_em` (TIMESTAMP). Eles não estão repetidos nas listas abaixo.
- Valores em dinheiro usam DECIMAL(15,2) em reais. Datas e horas ficam em UTC.
- Campos de status usam uma lista fechada de valores (ENUM), descrita em cada tabela.
- Dados de cliente nunca são apagados de verdade: usam `excluido_em` (exclusão lógica), por exigência regulatória.

## 1. Clientes e identidade

Este módulo guarda quem é o cliente e o que ele autorizou. Como o público tem pouco histórico, a renda informada e a ocupação entram já no cadastro para alimentar a análise de perfil.

**clientes**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| nome\_completo | VARCHAR(150) | Nome civil |
| nome\_social | VARCHAR(150) | Nome de tratamento, opcional |
| cpf | CHAR(11) | Único |
| data\_nascimento | DATE | Usada para validar maioridade |
| email | VARCHAR(150) | Único |
| telefone | VARCHAR(20) | Celular com DDD |
| renda\_mensal\_declarada | DECIMAL(15,2) | Informada pelo cliente |
| ocupacao | VARCHAR(100) | Profissão ou fonte de renda |
| tipo\_renda | ENUM | formal, informal, autonomo, beneficio, sem\_renda |
| status\_cadastro | ENUM | em\_analise, aprovado, reprovado, bloqueado, encerrado |
| status\_kyc | ENUM | pendente, validado, recusado |
| aceite\_termos\_em | TIMESTAMP | Data do aceite dos termos de uso |
| excluido\_em | TIMESTAMP | Exclusão lógica |

**enderecos**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| cep | CHAR(8) |  |
| logradouro | VARCHAR(150) |  |
| numero | VARCHAR(10) |  |
| complemento | VARCHAR(80) |  |
| bairro | VARCHAR(80) |  |
| cidade | VARCHAR(80) |  |
| uf | CHAR(2) |  |
| tipo | ENUM | residencial, correspondencia |
| principal | BOOLEAN | Indica o endereço principal |

**documentos\_cliente**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| tipo\_documento | ENUM | rg, cnh, selfie, comprovante\_residencia, comprovante\_renda |
| numero | VARCHAR(30) | Quando o documento tem número |
| url\_arquivo | VARCHAR(255) | Local do arquivo no armazenamento seguro |
| status\_validacao | ENUM | pendente, aprovado, recusado |
| validado\_em | TIMESTAMP |  |

**consentimentos\_lgpd**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| finalidade | ENUM | analise\_credito, marketing, compartilhamento\_parceiros, uso\_dados\_comportamentais |
| concedido | BOOLEAN | Sim ou não |
| versao\_termo | VARCHAR(20) | Versão do texto aceito |
| concedido\_em | TIMESTAMP |  |
| revogado\_em | TIMESTAMP | Preenchido se o cliente revogar |

## 2. Conta digital

A tabela `transacoes` é o extrato único da conta: todo dinheiro que entra ou sai passa por ela. É também a principal fonte de dados para a análise de comportamento.

**contas**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| agencia | CHAR(4) |  |
| numero\_conta | VARCHAR(12) | Único |
| digito | CHAR(1) |  |
| tipo\_conta | ENUM | pagamento, corrente |
| saldo\_disponivel | DECIMAL(15,2) | Atualizado a cada transação |
| saldo\_bloqueado | DECIMAL(15,2) | Valores retidos (ex.: judicial) |
| status | ENUM | ativa, bloqueada, encerrada |
| aberta\_em | TIMESTAMP |  |
| encerrada\_em | TIMESTAMP |  |

**transacoes**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| conta\_id | UUID | FK → contas |
| tipo | ENUM | pix\_enviado, pix\_recebido, ted, deposito, saque, pagamento\_boleto, compra\_debito, pagamento\_fatura, credito\_emprestimo, pagamento\_parcela, tarifa, estorno |
| direcao | ENUM | entrada, saida |
| valor | DECIMAL(15,2) | Sempre positivo; a direção diz o sinal |
| saldo\_apos | DECIMAL(15,2) | Saldo da conta após a transação |
| descricao | VARCHAR(150) | Texto do extrato |
| categoria\_id | UUID | FK → categorias (gestão financeira) |
| contraparte\_nome | VARCHAR(150) | Quem recebeu ou enviou |
| contraparte\_documento | VARCHAR(14) | CPF ou CNPJ |
| contraparte\_banco | VARCHAR(10) | Código do banco |
| id\_externo | VARCHAR(64) | Ex.: código end-to-end do Pix |
| status | ENUM | pendente, concluida, falhou, estornada |
| realizada\_em | TIMESTAMP |  |

**chaves\_pix**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| conta\_id | UUID | FK → contas |
| tipo\_chave | ENUM | cpf, email, telefone, aleatoria |
| valor\_chave | VARCHAR(77) | Único |
| status | ENUM | ativa, portabilidade, excluida |

**boletos**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| conta\_id | UUID | FK → contas |
| linha\_digitavel | VARCHAR(48) |  |
| beneficiario | VARCHAR(150) |  |
| valor | DECIMAL(15,2) |  |
| vencimento | DATE |  |
| status | ENUM | agendado, pago, vencido, cancelado |
| pago\_em | TIMESTAMP |  |
| transacao\_id | UUID | FK → transacoes, quando pago |

**favorecidos**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| nome | VARCHAR(150) |  |
| documento | VARCHAR(14) | CPF ou CNPJ |
| chave\_pix | VARCHAR(77) | Opcional |
| banco | VARCHAR(10) | Opcional, para TED |
| agencia | VARCHAR(5) | Opcional |
| conta | VARCHAR(15) | Opcional |

## 3. Cartões

O cartão de crédito não guarda o limite: o limite vem da tabela `limites_credito` (módulo 4). Assim, quando o limite sobe, ele vale para todos os cartões do cliente de uma vez.

**cartoes**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| conta\_id | UUID | FK → contas |
| formato | ENUM | fisico, virtual, virtual\_temporario |
| funcao | ENUM | debito, credito, multiplo |
| bandeira | VARCHAR(20) | Ex.: Visa, Mastercard |
| final\_cartao | CHAR(4) | Só os 4 últimos dígitos; o número completo fica com o processador |
| token\_processador | VARCHAR(64) | Referência segura ao cartão no processador |
| nome\_impresso | VARCHAR(26) |  |
| validade | CHAR(5) | MM/AA |
| dia\_vencimento\_fatura | INT | Dia do mês, de 1 a 28 |
| aproximacao\_ativa | BOOLEAN |  |
| compras\_internacionais | BOOLEAN |  |
| status | ENUM | solicitado, em\_transporte, ativo, bloqueado\_temporario, cancelado |
| emitido\_em | TIMESTAMP |  |

**compras\_cartao**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cartao\_id | UUID | FK → cartoes |
| estabelecimento | VARCHAR(150) |  |
| mcc | CHAR(4) | Código do ramo do comércio |
| categoria\_id | UUID | FK → categorias |
| valor\_total | DECIMAL(15,2) |  |
| num\_parcelas | INT | 1 para compra à vista |
| funcao\_usada | ENUM | debito, credito |
| status | ENUM | autorizada, negada, cancelada, estornada |
| motivo\_negativa | VARCHAR(100) | Ex.: limite insuficiente |
| realizada\_em | TIMESTAMP |  |

**faturas**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| mes\_referencia | CHAR(7) | AAAA-MM |
| data\_fechamento | DATE |  |
| data\_vencimento | DATE |  |
| valor\_total | DECIMAL(15,2) |  |
| valor\_minimo | DECIMAL(15,2) |  |
| valor\_pago | DECIMAL(15,2) |  |
| pago\_em | TIMESTAMP | Usado para saber se pagou em dia |
| status | ENUM | aberta, fechada, paga, paga\_parcial, atrasada |
| dias\_atraso | INT | Calculado após o vencimento |

**lancamentos\_fatura**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| fatura\_id | UUID | FK → faturas |
| compra\_id | UUID | FK → compras\_cartao; vazio para juros e tarifas |
| tipo | ENUM | compra, parcela, juros, multa, tarifa, estorno, pagamento |
| numero\_parcela | INT | Ex.: 2 (de 6) |
| valor | DECIMAL(15,2) |  |
| descricao | VARCHAR(150) |  |

## 4. Análise de perfil e crédito progressivo

Este é o módulo que cumpre o propósito da Vértis. O fluxo funciona assim:

1. Cada ação do cliente gera um registro em `eventos_comportamentais`.
2. Esses eventos consolidam os indicadores em `perfil_financeiro`.
3. Os indicadores geram uma nota em `scores_credito`.
4. As `regras_progressao_credito` dizem quanto o limite pode subir.
5. O resultado fica em `limites_credito`, e cada mudança vai para `historico_limite`.

**eventos\_comportamentais**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| tipo\_evento | ENUM | fatura\_paga\_em\_dia, fatura\_atrasada, deposito\_recebido, salario\_recebido, compra\_realizada, acesso\_app, meta\_atingida, open\_finance\_conectado, parcela\_paga, saldo\_negativo |
| origem | ENUM | conta, cartao, emprestimo, open\_finance, app |
| referencia\_id | UUID | Id do registro que gerou o evento (fatura, transação etc.) |
| valor | DECIMAL(15,2) | Quando o evento tem valor |
| impacto | ENUM | positivo, neutro, negativo |
| dados\_extras | JSON | Detalhes livres do evento |
| ocorrido\_em | TIMESTAMP |  |

**perfil\_financeiro**

Uma linha por cliente, recalculada sempre que entra um evento novo.

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes, único |
| renda\_media\_comprovada | DECIMAL(15,2) | Média de entradas reais dos últimos 3 meses |
| gasto\_medio\_mensal | DECIMAL(15,2) |  |
| comprometimento\_renda | DECIMAL(5,2) | % da renda já usada em dívidas |
| faturas\_pagas\_em\_dia | INT | Contagem acumulada |
| faturas\_atrasadas | INT | Contagem acumulada |
| maior\_atraso\_dias | INT |  |
| meses\_de\_relacionamento | INT | Tempo de conta na Vértis |
| frequencia\_uso\_app | INT | Acessos nos últimos 30 dias |
| tem\_open\_finance | BOOLEAN | Se há contas externas conectadas |
| saldo\_medio | DECIMAL(15,2) | Média dos últimos 3 meses |
| perfil\_risco | ENUM | muito\_baixo, baixo, medio, alto, muito\_alto |
| atualizado\_em | TIMESTAMP |  |

**scores\_credito**

Histórico de notas. A mais recente é a que vale.

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| score\_interno | INT | Nota de 0 a 1000 calculada pela Vértis |
| score\_bureau | INT | Nota externa (ex.: Serasa), se consultada |
| versao\_modelo | VARCHAR(20) | Versão do algoritmo que calculou |
| fatores\_positivos | JSON | O que ajudou a nota |
| fatores\_negativos | JSON | O que puxou a nota para baixo |
| calculado\_em | TIMESTAMP |  |

**limites\_credito**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes, único |
| limite\_total | DECIMAL(15,2) | Limite atual do cartão |
| limite\_utilizado | DECIMAL(15,2) |  |
| limite\_disponivel | DECIMAL(15,2) | Total menos utilizado |
| limite\_emprestimo\_pre\_aprovado | DECIMAL(15,2) |  |
| proximo\_limite\_previsto | DECIMAL(15,2) | Valor mostrado na tela de evolução |
| proxima\_revisao\_em | DATE | Quando o limite será reavaliado |

**historico\_limite**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| limite\_anterior | DECIMAL(15,2) |  |
| limite\_novo | DECIMAL(15,2) |  |
| motivo | ENUM | aumento\_automatico, solicitacao\_cliente, reducao\_risco, subida\_nivel, open\_finance |
| score\_id | UUID | FK → scores\_credito que justificou |
| regra\_id | UUID | FK → regras\_progressao\_credito aplicada |
| alterado\_em | TIMESTAMP |  |

**regras\_progressao\_credito**

Parâmetros que a equipe ajusta sem mudar o código.

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| nome | VARCHAR(100) | Ex.: "3 faturas em dia" |
| score\_minimo | INT |  |
| faturas\_em\_dia\_minimas | INT |  |
| meses\_minimos | INT | Tempo mínimo de conta |
| percentual\_aumento | DECIMAL(5,2) | Quanto o limite sobe |
| limite\_maximo | DECIMAL(15,2) | Teto que a regra pode alcançar |
| ativa | BOOLEAN |  |

## 5. Empréstimo personalizado

A proposta usa o score e o perfil do momento para personalizar taxa e prazo. Cada parcela paga gera um evento positivo no módulo 4.

**propostas\_emprestimo**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| score\_id | UUID | FK → scores\_credito usado na oferta |
| valor\_solicitado | DECIMAL(15,2) |  |
| valor\_aprovado | DECIMAL(15,2) |  |
| num\_parcelas | INT |  |
| taxa\_juros\_mensal | DECIMAL(5,2) | % ao mês |
| cet\_anual | DECIMAL(6,2) | Custo efetivo total, obrigatório por lei |
| valor\_parcela | DECIMAL(15,2) |  |
| finalidade | VARCHAR(100) | Ex.: quitar dívida, capital de giro |
| status | ENUM | simulada, enviada, aprovada, recusada, expirada, contratada |
| validade\_ate | TIMESTAMP | Prazo da oferta |

**contratos\_emprestimo**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| proposta\_id | UUID | FK → propostas\_emprestimo |
| cliente\_id | UUID | FK → clientes |
| conta\_id | UUID | FK → contas onde o dinheiro cai |
| numero\_contrato | VARCHAR(20) | Único |
| valor\_contratado | DECIMAL(15,2) |  |
| saldo\_devedor | DECIMAL(15,2) |  |
| data\_primeira\_parcela | DATE |  |
| status | ENUM | ativo, quitado, em\_atraso, renegociado, cancelado |
| assinado\_em | TIMESTAMP |  |
| quitado\_em | TIMESTAMP |  |

**parcelas\_emprestimo**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| contrato\_id | UUID | FK → contratos\_emprestimo |
| numero\_parcela | INT |  |
| valor | DECIMAL(15,2) |  |
| vencimento | DATE |  |
| valor\_pago | DECIMAL(15,2) |  |
| pago\_em | TIMESTAMP |  |
| juros\_atraso | DECIMAL(15,2) |  |
| status | ENUM | a\_vencer, paga, paga\_atrasada, vencida |
| transacao\_id | UUID | FK → transacoes do pagamento |

## 6. Open Finance

O Open Finance traz o histórico que o cliente tem em outros bancos. Para quem tem pouco histórico na Vértis, isso acelera o aumento de limite. Os dados só podem ser lidos enquanto o consentimento estiver válido.

**instituicoes\_financeiras**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| nome | VARCHAR(100) |  |
| codigo\_banco | CHAR(3) | Código COMPE |
| cnpj | CHAR(14) |  |
| participa\_open\_finance | BOOLEAN |  |
| url\_logo | VARCHAR(255) | Para mostrar no app |

**consentimentos\_open\_finance**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| instituicao\_id | UUID | FK → instituicoes\_financeiras |
| id\_consentimento\_externo | VARCHAR(100) | Id gerado no ecossistema Open Finance |
| permissoes | JSON | Ex.: contas, cartões, transações, operações de crédito |
| status | ENUM | aguardando\_autorizacao, autorizado, rejeitado, revogado, expirado |
| autorizado\_em | TIMESTAMP |  |
| expira\_em | TIMESTAMP | Prazo máximo de 12 meses |
| revogado\_em | TIMESTAMP |  |
| ultima\_sincronizacao\_em | TIMESTAMP |  |

**contas\_externas**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| consentimento\_id | UUID | FK → consentimentos\_open\_finance |
| tipo\_produto | ENUM | conta\_corrente, poupanca, cartao\_credito, emprestimo, financiamento |
| identificador\_externo | VARCHAR(100) | Id da conta no outro banco |
| saldo | DECIMAL(15,2) | Último saldo lido |
| limite | DECIMAL(15,2) | Para cartões e cheque especial |
| saldo\_devedor | DECIMAL(15,2) | Para empréstimos e financiamentos |
| atualizado\_em | TIMESTAMP |  |

**transacoes\_externas**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| conta\_externa\_id | UUID | FK → contas\_externas |
| id\_externo | VARCHAR(100) | Evita importar a mesma transação duas vezes |
| tipo | VARCHAR(50) | Como o outro banco classificou |
| direcao | ENUM | entrada, saida |
| valor | DECIMAL(15,2) |  |
| descricao | VARCHAR(150) |  |
| categoria\_id | UUID | FK → categorias |
| eh\_renda\_recorrente | BOOLEAN | Marcado pela análise (ex.: salário) |
| realizada\_em | TIMESTAMP |  |

## 7. Gamificação: níveis, pontos, milhas e conquistas

Este módulo alimenta a tela de evolução. O cliente acumula três coisas diferentes: XP (faz subir de nível), pontos e milhas (podem ser trocados). Todo ganho ou gasto vira uma linha em `movimentacoes_recompensa`, que funciona como extrato.

**niveis**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| ordem | INT | 1 = primeiro nível |
| nome | VARCHAR(50) | Ex.: Semente, Bronze, Prata, Ouro, Platina, Black |
| xp\_minimo | INT | XP necessário para entrar no nível |
| multiplicador\_pontos | DECIMAL(4,2) | Ex.: 1.5 = 50% a mais de pontos |
| cor\_hex | CHAR(7) | Cor usada na tela |
| url\_icone | VARCHAR(255) |  |

**progresso\_cliente**

Uma linha por cliente. É o que a tela de evolução lê em tempo real.

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes, único |
| nivel\_id | UUID | FK → niveis, nível atual |
| xp\_total | INT |  |
| xp\_para\_proximo\_nivel | INT |  |
| saldo\_pontos | INT |  |
| saldo\_milhas | INT |  |
| sequencia\_dias\_ativos | INT | Dias seguidos usando o app |
| proxima\_conquista\_id | UUID | FK → conquistas, destaque "Próxima conquista" |
| subiu\_nivel\_em | TIMESTAMP | Última subida de nível |

**regras\_pontuacao**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| tipo\_evento | ENUM | Mesmos valores de eventos\_comportamentais.tipo\_evento |
| xp\_ganho | INT |  |
| pontos\_ganhos | INT |  |
| milhas\_ganhas | INT |  |
| pontos\_por\_real | DECIMAL(6,2) | Para eventos com valor, como compras |
| limite\_diario | INT | Evita abuso (ex.: abrir o app 50 vezes) |
| ativa | BOOLEAN |  |
| valida\_de | DATE | Para campanhas com data |
| valida\_ate | DATE |  |

**movimentacoes\_recompensa**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| moeda | ENUM | xp, pontos, milhas |
| tipo | ENUM | credito, debito, expiracao, estorno |
| quantidade | INT |  |
| saldo\_apos | INT |  |
| evento\_id | UUID | FK → eventos\_comportamentais que gerou |
| regra\_id | UUID | FK → regras\_pontuacao aplicada |
| resgate\_id | UUID | FK → resgates, quando é um gasto |
| descricao | VARCHAR(150) | Ex.: "Fatura paga em dia" |
| expira\_em | DATE | Validade dos pontos ou milhas |
| ocorrido\_em | TIMESTAMP |  |

**conquistas**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| codigo | VARCHAR(50) | Único, ex.: FATURA\_EM\_DIA\_6X |
| nome | VARCHAR(100) | Ex.: Fatura em Dia, Open Finance Conectado |
| descricao | VARCHAR(255) |  |
| categoria | ENUM | pagamento, uso, credito, viagem, educacao\_financeira |
| criterio\_tipo\_evento | ENUM | Evento que conta para a conquista |
| criterio\_quantidade | INT | Ex.: 6 faturas em dia |
| nivel\_minimo\_id | UUID | FK → niveis, se exige nível |
| xp\_recompensa | INT |  |
| pontos\_recompensa | INT |  |
| beneficio\_id | UUID | FK → beneficios que a conquista libera |
| url\_icone | VARCHAR(255) |  |
| ativa | BOOLEAN |  |

**conquistas\_cliente**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| conquista\_id | UUID | FK → conquistas |
| progresso\_atual | INT | Ex.: 4 de 6 |
| status | ENUM | bloqueada, em\_andamento, conquistada |
| conquistada\_em | TIMESTAMP |  |
| visualizada | BOOLEAN | Para mostrar a animação só uma vez |

**beneficios**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| nome | VARCHAR(100) | Ex.: Sala VIP Aeroporto, Multiplicador de Pontos |
| tipo | ENUM | sala\_vip, multiplicador, cashback, isencao\_tarifa, aumento\_limite, desconto\_parceiro |
| parceiro\_id | UUID | FK → parceiros, quando há |
| nivel\_minimo\_id | UUID | FK → niveis |
| usos\_por\_mes | INT | Ex.: 2 acessos à sala VIP |
| valor | DECIMAL(10,2) | % ou valor do benefício |
| ativo | BOOLEAN |  |

**beneficios\_cliente**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| beneficio\_id | UUID | FK → beneficios |
| origem | ENUM | nivel, conquista, campanha |
| status | ENUM | liberado, utilizado, expirado |
| usos\_restantes | INT |  |
| codigo\_voucher | VARCHAR(50) | Ex.: código de acesso à sala VIP |
| liberado\_em | TIMESTAMP |  |
| expira\_em | TIMESTAMP |  |

**parceiros**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| nome | VARCHAR(100) | Ex.: companhia aérea, rede de salas VIP |
| tipo | ENUM | companhia\_aerea, sala\_vip, varejo, programa\_fidelidade |
| taxa\_conversao | DECIMAL(6,2) | Quantos pontos valem 1 milha do parceiro |
| ativo | BOOLEAN |  |

**resgates**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| tipo | ENUM | transferencia\_milhas, cashback, produto, desconto\_fatura |
| parceiro\_id | UUID | FK → parceiros |
| moeda\_usada | ENUM | pontos, milhas |
| quantidade\_usada | INT |  |
| valor\_equivalente | DECIMAL(15,2) | Em reais |
| status | ENUM | solicitado, processando, concluido, falhou |
| solicitado\_em | TIMESTAMP |  |
| concluido\_em | TIMESTAMP |  |

## 8. Gestão financeira

Este módulo dá ao cliente o controle do próprio dinheiro. As categorias servem às transações da conta, às compras no cartão e às transações externas. Cumprir orçamentos e metas também gera pontos e eventos positivos.

**categorias**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| nome | VARCHAR(50) | Ex.: Alimentação, Transporte, Moradia |
| categoria\_pai\_id | UUID | FK → categorias, para subcategorias |
| cliente\_id | UUID | FK → clientes; vazio = categoria padrão da Vértis |
| tipo | ENUM | despesa, receita |
| icone | VARCHAR(50) |  |
| cor\_hex | CHAR(7) |  |

**orcamentos**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| categoria\_id | UUID | FK → categorias |
| mes\_referencia | CHAR(7) | AAAA-MM |
| valor\_planejado | DECIMAL(15,2) |  |
| valor\_gasto | DECIMAL(15,2) | Atualizado a cada transação |
| alerta\_percentual | INT | Ex.: avisar ao atingir 80% |
| status | ENUM | dentro, alerta, estourado |

**metas\_financeiras**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| nome | VARCHAR(100) | Ex.: Reserva de emergência, Viagem |
| valor\_alvo | DECIMAL(15,2) |  |
| valor\_atual | DECIMAL(15,2) |  |
| data\_alvo | DATE |  |
| aporte\_automatico | DECIMAL(15,2) | Valor guardado todo mês, opcional |
| status | ENUM | ativa, concluida, cancelada |
| concluida\_em | TIMESTAMP |  |

## 9. Segurança, notificações e auditoria

Um banco precisa provar quem fez o quê e quando. As senhas nunca ficam guardadas como texto: só o hash, de preferência com um serviço de autenticação dedicado.

**dispositivos**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| identificador\_dispositivo | VARCHAR(100) | Id único do aparelho |
| modelo | VARCHAR(100) |  |
| sistema\_operacional | VARCHAR(50) |  |
| token\_push | VARCHAR(255) | Para enviar notificações |
| confiavel | BOOLEAN | Liberado após validação |
| biometria\_ativa | BOOLEAN |  |
| ultimo\_acesso\_em | TIMESTAMP |  |

**sessoes\_acesso**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| dispositivo\_id | UUID | FK → dispositivos |
| ip | VARCHAR(45) |  |
| localizacao\_aproximada | VARCHAR(100) | Cidade e estado |
| metodo\_login | ENUM | senha, biometria, token |
| sucesso | BOOLEAN | Tentativas falhas também ficam registradas |
| iniciada\_em | TIMESTAMP |  |
| encerrada\_em | TIMESTAMP |  |

**notificacoes**

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| cliente\_id | UUID | FK → clientes |
| tipo | ENUM | transacao, fatura, limite, conquista, nivel, seguranca, promocao |
| canal | ENUM | push, email, sms, app |
| titulo | VARCHAR(100) | Ex.: "Sala VIP Aeroporto liberada!" |
| mensagem | VARCHAR(500) |  |
| referencia\_id | UUID | Registro ligado (conquista, fatura etc.) |
| lida | BOOLEAN |  |
| enviada\_em | TIMESTAMP |  |
| lida\_em | TIMESTAMP |  |

**logs\_auditoria**

Registro que nunca é editado nem apagado.

| Atributo | Tipo | Descrição |
| --- | --- | --- |
| id | UUID | Chave primária |
| ator\_tipo | ENUM | cliente, funcionario, sistema |
| ator\_id | UUID | Quem fez a ação |
| acao | VARCHAR(50) | Ex.: alterou\_limite, bloqueou\_cartao |
| tabela\_afetada | VARCHAR(50) |  |
| registro\_id | UUID |  |
| valores\_antes | JSON |  |
| valores\_depois | JSON |  |
| ip | VARCHAR(45) |  |
| ocorrido\_em | TIMESTAMP |  |

## 10. Como os módulos se conectam

A tabela `eventos_comportamentais` é o ponto de encontro de tudo. A mesma ação, como pagar a fatura em dia, segue por duas trilhas: melhora o score e o limite, e também gera XP, pontos e milhas.

&#91;embedded content: fluxo de dados · 5 fontes, 2 trilhas, 1 tela\]

Próximo passo: transformar este roteiro no diagrama entidade-relacionamento e definir índices e chaves únicas antes de o script em Python começar.
