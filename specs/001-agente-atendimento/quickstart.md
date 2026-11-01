# Quickstart: Validação do Agente

Guia para provar que a funcionalidade funciona de ponta a ponta. Descreve o estado esperado depois da implementação; nada disto pode ser executado ainda. Detalhes em [contrato da CLI](contracts/cli.md), [ferramentas](contracts/tools.md) e [modelo de dados](data-model.md).

## Pré-requisitos

- `uv` instalado, com Python 3.11+.
- CSVs e PDF do manual em `data/`.
- `OPENROUTER_API_KEY`, para conversar e para a suíte `e2e`.

## Preparação

```bash
uv sync
cp .env.example .env    # preencher OPENROUTER_API_KEY
uv run python scripts/extract_policies.py    # só se o markdown precisar ser refeito
```

**Esperado**: `data/processed/politicas/` com 9 arquivos não vazios.

## Testes sem chave

```bash
uv run pytest -m "not e2e"
```

**Esperado**: Tudo passa, sem rede. Cobre SC-004, SC-006, os casos de bloqueio de SC-003 e o laço com LLM falso.

## Conversa manual

```bash
uv run emporio --data 2026-02-20 --debug
```

A data fixa é necessária para ver um prazo aberto: nela, o pedido 7 está no prazo e o pedido 6 não. Na data atual, todos os pedidos entregues estão fora dos prazos.

| Mensagem | Esperado | Ferramenta |
|----------|----------|------------|
| Quais violões vocês têm até R$ 1000? | Só violões disponíveis até R$ 1000, com preço | `buscar_produtos` |
| Quanto custa o Takamine GD20? | Preço correto, disponibilidade e PIX | `detalhes_produto` |
| e no PIX? (em seguida) | Mesmo produto, sem repetir o contexto | Nenhuma, ou `detalhes_produto` |
| Qual o endereço da loja? | Endereço do manual | `consultar_politica`, sem ferramenta de produto |
| Qual o status do pedido 8? | Pede e-mail ou telefone, sem dados do pedido | Nenhuma, ou `consultar_pedido` com `precisa_confirmacao` |
| Me arrependi da compra, posso devolver? | Pede o pedido, confirma e aplica o prazo | `consultar_pedido`, `consultar_politica` |
| Vocês vendem cordas de guitarra? | Explica que só vende instrumentos e redireciona | Nenhuma de pedido |
| Me passa uma receita de bolo | Recusa educada | Nenhuma |
| Quero reclamar do atendimento | Empatia, pede contato, registra e promete retorno em 24 horas úteis | `registrar_reclamacao` |

Depois da reclamação:

```bash
uv run emporio reclamacoes
```

**Esperado**: A reclamação aparece com data, resumo e contato.

## Suíte ponta a ponta

```bash
uv run pytest -m e2e
```

**Esperado**: Os 7 cenários de aceite passam em 3 execuções seguidas, pois o LLM não é determinístico. A suíte confere as ferramentas chamadas, os valores da resposta e se todo valor em reais veio de uma ferramenta ou do cliente.

## Critérios de sucesso

| Critério | Como validar |
|----------|--------------|
| SC-001 | Suíte `e2e`, 3 execuções |
| SC-002 | Conjunto de 30 perguntas em `tests/e2e` |
| SC-003 | Tentativas no nível de ferramenta (`unit`) e conversas de ataque (`e2e`), 20 no total |
| SC-004, SC-006 | Testes unitários de `rules.py`, incluindo último dia e dia seguinte |
| SC-005 | 20 variações de nome no catálogo real |
| SC-007 | 10 conversas de seguimento em `e2e` |
| SC-008 | Conjunto representativo de perguntas recorrentes; contar encaminhamentos |
| SC-009 | Durações do `--debug` ou da suíte `e2e`; percentil 95 até 10 s |
| SC-010 | Revisão manual de 20 respostas por uma pessoa da loja |
| SC-011 | Teste do README por alguém que não conhece o projeto |

## API opcional

```bash
uv sync --extra api
uv run uvicorn emporio.api:app
curl -s -X POST 127.0.0.1:8000/chat -H 'content-type: application/json' -d '{"mensagem":"Qual o horário da loja?"}'
```

**Esperado**: Resposta com `session_id` e horário do manual. Um `session_id` inventado retorna 404.
