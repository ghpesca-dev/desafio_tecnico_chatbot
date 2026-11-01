# Data Model: Agente de Atendimento da Empório da Música

Colunas e valores conferidos com os arquivos em `data/` em 2026-11-01. Os CSVs mantêm o nome original (`desafio_tecnico_ai_eng - <tabela>.csv`).

## Fontes (somente leitura)

### Produto (`products`, 65 linhas)

| Campo | Tipo | Regra |
|-------|------|-------|
| `product_id` | int | Único; ids de 81 a 145 |
| `name` | texto | Obrigatório; sem duplicatas |
| `category_id` | int | Referencia Categoria |
| `description` | texto | |
| `price_brl` | `Decimal` | Maior que zero; sem preço, o produto é tratado como dado incompleto |
| `stock_quantity` | int | Maior ou igual a zero; nunca enviado ao LLM (FR-013) |
| `status` | enum | `active`, `discontinued`, `coming_soon` |
| `specs` | JSON em texto | Convertido em dicionário; JSON inválido vira `{}` com aviso no log |
| `created_at` | data | Não usado |

**Campos derivados**: `categoria`, `nome_normalizado`, `promocao_ativa`, `promocao_encerrada`, `preco_atual`.

**Situação para o cliente**: `status` prevalece sobre o estoque.

| Condição | `situacao` | Aparece na busca |
|----------|-----------|------------------|
| `active` e `stock_quantity > 0` | `disponivel` | Sim |
| `active` e `stock_quantity = 0` | `temporariamente_indisponivel` | Não |
| `discontinued`, com qualquer estoque | `fora_de_catalogo` | Não |
| `coming_soon`, com qualquer estoque | `em_breve` | Não |
| Preço, estoque ou categoria inválidos | `sem_informacao` | Não |

### Categoria (`categories`, 9 linhas)

`category_id`, `name` e `description`. As categorias 6, 7 e 8 (sopros e cordas orquestrais) não têm produtos (FR-036).

### Promoção (`promotions`, 25 linhas)

| Campo | Tipo | Regra |
|-------|------|-------|
| `promotion_id` | int | Único |
| `product_id` | int | Referencia Produto |
| `discount_percent` | `Decimal` | Percentual sobre `price_brl` |
| `description` | texto | Nome da campanha |
| `is_active` | 0 ou 1 | Não há datas de validade |

**Ativa**: `is_active = 1`. Se houver várias, vale a de maior desconto.

**Encerrada**: `is_active = 0`. Se houver várias, vale a de maior `promotion_id`.

**Promoções ativas hoje**: 127 (10%), 121 (20%), 90 (18%) e 94 (8%).

### Pedido (`orders`, 20 linhas)

| Campo | Tipo | Regra |
|-------|------|-------|
| `order_id` | int | Número informado pelo cliente |
| `customer_id` | int | Referencia Cliente; nunca enviado ao LLM |
| `order_date` | data | Data da compra; base do prazo de defeito |
| `status` | enum | Veja a tabela abaixo |
| `total_brl` | `Decimal` | O total registrado prevalece sobre a soma dos itens (FR-028) |
| `payment_method` | enum | `pix`, `debit`, `boleto`, `credit_3x`, `credit_6x`, `credit_12x` |
| `tracking_code` | texto ou vazio | |
| `estimated_delivery` | data ou vazio | Aproxima a data de recebimento |
| `notes` | texto ou vazio | Motivo do cancelamento |

| `status` | Texto ao cliente | Prazos de troca |
|----------|------------------|-----------------|
| `pending` | pendente | `nao_iniciado` |
| `confirmed` | confirmado | `nao_iniciado` |
| `shipped` | enviado | `nao_iniciado` |
| `delivered` | entregue | Calculados |
| `cancelled` | cancelado | `nao_se_aplica` |

| `payment_method` | Texto ao cliente |
|------------------|------------------|
| `pix` | PIX |
| `debit` | cartão de débito |
| `boleto` | boleto |
| `credit_Nx` | cartão de crédito em Nx |

### Item de pedido (`order_items`, 22 linhas)

`order_id`, `product_id` e `quantity`. Não há preço pago, portanto o item é mostrado só com nome e quantidade.

### Cliente (`customers`, 50 linhas)

`customer_id`, `name`, `phone` (formato `(67) 99999-9999`), `email` e `city`. Fica em memória, dentro do repositório. Saem da camada de dados apenas o resultado da comparação e, depois da confirmação, `primeiro_nome`. Um e-mail se repete entre dois clientes, por isso a comparação é só com o dono do pedido.

### Política

Um arquivo por tópico em `data/processed/politicas/`: `loja`, `horario`, `pagamento`, `trocas_devolucoes`, `frete`, `promocoes`, `atendimento`, `garantia`, `privacidade`. Todos são obrigatórios e não podem estar vazios.

## Estado de execução

### Sessão (`SessionState`, em memória)

| Campo | Regra |
|-------|-------|
| `id` | UUID4 |
| `mensagens` | Histórico; janela de 10 trocas |
| `pedidos_confirmados` | Conjunto de números; só cresce na sessão |
| `falhas_confirmacao` | Soma de 1 por falha; em 3, a consulta é bloqueada |
| `mensagens_cliente_recentes` | Textos do cliente desde a última confirmação; limpo a cada sucesso |

**Transições da consulta de um pedido**:

```text
sem confirmação ─ dados corretos ─────────► confirmado (só este pedido, nesta sessão)
sem confirmação ─ falha (1ª ou 2ª) ───────► sem confirmação, com contador maior
sem confirmação ─ 3ª falha ───────────────► bloqueado (até o fim da sessão)
bloqueado ─ qualquer tentativa ───────────► bloqueado, sem consultar os dados
```

Um dado que o cliente não escreveu depois da última confirmação não vale nem conta como falha. Bloqueio afeta novas confirmações; pedidos já confirmados continuam acessíveis na sessão.

### Reclamação (`data/runtime/reclamacoes.jsonl`)

| Campo | Regra |
|-------|-------|
| `id` | UUID4 |
| `registrada_em` | Data e hora com fuso |
| `sessao_id` | Texto |
| `resumo` | Obrigatório, não vazio |
| `contato` | Obrigatório, não vazio |
| `nome`, `pedido` | Opcionais; número do pedido informado pelo cliente, sem conferência |

Só acrescenta registros. Dados pessoais: arquivo fora do Git.

## Relacionamentos

```text
Categoria 1 ─ N Produto 1 ─ N Promoção
Cliente 1 ─ N Pedido 1 ─ N Item de pedido N ─ 1 Produto
Sessão 1 ─ N Reclamação
```

## Validação na inicialização

- Colunas obrigatórias faltando interrompem a inicialização, com a lista do que faltou.
- Referências quebradas e dados incompletos geram aviso e tornam o registro indisponível, sem preencher valores.
- Pedidos cujo total difere da soma pelo preço atual geram aviso. Hoje são os pedidos 3 e 20.
- O catálogo deve ter 65 produtos; um número diferente gera aviso.
