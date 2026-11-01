# Research: Agente de Atendimento da Empório da Música

Pesquisa feita em 2026-11-01. Foram verificados, nessa data, a lista pública de modelos do OpenRouter, a documentação de roteamento, a resolução das dependências para Python 3.11, os seis CSVs e o manual. Nenhuma chamada a um LLM foi feita.

## R-01 Dados de origem conferidos

- **Decision**: O [modelo de dados](data-model.md) usa as colunas reais. O loader valida as colunas na inicialização e falha com a lista do que faltou.
- **Achados que mudaram o design**:
  - `promotions` não tem datas: ativa significa `is_active = 1`.
  - `order_items` não tem preço: a resposta sobre itens traz nome e quantidade, sem valor. O preço atual do catálogo não é o valor pago.
  - O prazo de defeito conta da compra, não do recebimento (seção 4.2 do manual).
  - Parcelas de 2x e 3x têm mínimo de R$ 50 (seção 3.1), o que a tabela da seção 3 não diz.
- **Achados confirmados**: 65 produtos, sem preço vazio e com `specs` válidos. Só os pedidos 3 e 20 têm total diferente da soma pelo preço atual. A promoção de menor desconto ativa é de 8%, então a regra do PIX não prejudica nenhum cliente hoje.
- **Anomalias que o código deve tolerar**: Produto 136 descontinuado com estoque 13; produto 130 `coming_soon` com estoque 2 e presente nos pedidos 3 e 14; `bruno.martins@jmail.com` em dois clientes; parcelas históricas abaixo do mínimo nos pedidos 9, 16 e 18.
- **Rationale**: `status` prevalece sobre estoque, e a identidade só é comparada com o dono daquele pedido, então o e-mail repetido não abre pedido de outra pessoa.
- **Alternatives considered**: Inventar validade para promoções, rejeitado porque seria dado sem fonte.

## R-02 Modelo e parâmetros do LLM

- **Decision**: Padrão `OPENROUTER_MODEL=anthropic/claude-sonnet-5.5`. `anthropic/claude-haiku-5.5` é a alternativa barata a medir na suíte. Enviar `extra_body={"provider": {"require_parameters": true}}`. Temperatura em `OPENROUTER_TEMPERATURE`, opcional e não enviada por padrão.
- **Rationale**: Os dois modelos listam `tools` e `tool_choice`. Preços listados por 1 milhão de tokens: Sonnet 5.5 a US$ 2 na entrada e US$ 10 na saída; Haiku 5.5 a US$ 0,10 e US$ 0,50. Nenhum dos dois, nem o Opus 5.5 ou os GPT 6.x consultados, lista `temperature`. A documentação diz que `require_parameters` exclui provedores sem suporte a algum parâmetro enviado, e que, sem ele, um parâmetro de ferramentas pode ser ignorado quando nenhum provedor o suporta. Por isso, enviar `temperature` com essa opção poderia excluir os provedores do modelo; por inferência da regra geral, pois a documentação não cita esse parâmetro nem o que ocorre quando nenhum provedor sobra.
- **Alternatives considered**: `require_parameters` falso, rejeitado porque um modelo sem ferramentas responderia sem consultar as fontes, violando FR-003. Gemini 4 Argon, que aceita `temperature`, fica como opção por variável de ambiente, sem vantagem que justifique ser o padrão.
- **Pendente**: A escolha final entre Sonnet e Haiku depende da suíte ponta a ponta (exatidão e SC-009). Isso exige chave.

## R-03 Orquestração

- **Decision**: Laço escrito à mão com limite de 6 iterações por turno. Se houver várias chamadas de ferramenta na mesma resposta, são executadas em sequência. Falha de LLM desfaz o turno no histórico, para não deixar chamada sem resultado. Se o limite for atingido, a resposta é o fallback com o telefone da loja.
- **Rationale**: Transparente e fácil de testar com um cliente falso. O SDK já oferece retry (`max_retries=2`) e `timeout=30`, então não há retry próprio.
- **Proteção adicionada após os testes reais**: Com `qwen/qwen3.5-9b`, o modelo encerrava o turno prometendo consultar, sem chamar ferramenta. Se a resposta traz essa promessa e nada foi consultado no turno, o laço repete a chamada uma vez com `tool_choice="required"`.
- **Alternatives considered**: LangChain ou LangGraph, rejeitados pelo input: não há ramificação ou multiagente que justifique. RAG e text-to-SQL, rejeitados porque deixariam exatidão e controle de acesso nas mãos do modelo.

## R-04 Verificação de identidade no código

- **Decision**: `SessionState` guarda pedidos confirmados, falhas e as mensagens do cliente desde a última confirmação. O LLM não lê nem altera esse estado.
  - Dado de contato só é aceito se o cliente o escreveu nessas mensagens. Assim, o modelo não reutiliza o e-mail do pedido 1 para abrir o pedido 2 (FR-026).
  - Pedido inexistente e dado incorreto recebem o mesmo erro e contam como falha (FR-024).
  - Depois de 3 falhas, a ferramenta recusa sem consultar os dados (FR-025). O estado fica fora do histórico, então cortar a janela não zera a contagem.
  - Dado reutilizado que o cliente não escreveu de novo não conta como falha, e a ferramenta pede o dado ao cliente.
- **Comparação**: E-mail sem diferença de caixa e espaços. Telefone só com dígitos, sem o `55`, aceitando sem DDD se ao menos os 8 últimos dígitos coincidirem. O dado é comparado apenas com o dono daquele pedido.
- **Rationale**: FR-022 exige que nenhuma mensagem contorne a regra. Como o modelo nunca recebe e-mail ou telefone do cadastro, não tem como fornecer um dado válido por conta própria.
- **Alternatives considered**: Regra só no prompt, rejeitada por FR-022.
- **Limitação**: Na CLI, nova sessão zera o contador. O bloqueio é por sessão, como pede o FR-025.

## R-05 Regras de negócio determinísticas

- **Decision**: Funções puras em `rules.py`, com `Decimal` e arredondamento `ROUND_HALF_UP`.
  - **Promoção ativa**: `is_active = 1`. Se houver mais de uma, vale a de maior desconto. Os dados atuais não têm esse caso.
  - **Promoção encerrada**: A linha `is_active = 0` do produto, de maior `promotion_id` se houver mais de uma. Só é informada se não houver promoção ativa.
  - **PIX**: 5% sobre o preço de tabela sem promoção. Com promoção, vale o preço promocional, e a saída indica `pix_nao_acumula` (seção 6.2 do manual).
  - **Parcelas**: Sem juros, sobre o preço atual. 1x sem mínimo; 2x e 3x com mínimo de R$ 50; 4x a 6x com mínimo de R$ 80; 7x a 12x com mínimo de R$ 100. A comparação usa o valor exato, antes de arredondar. A ferramenta devolve toda a tabela permitida, para o modelo não precisar calcular.
  - **Prazos**: Para pedidos entregues, com o último dia incluído. Arrependimento (7 dias), troca por preferência (7 dias) e garantia legal (90 dias) contam de `estimated_delivery`; defeito (30 dias) conta de `order_date`. Sem data, o resultado é `indeterminado`, e a orientação é encaminhar (FR-033).
  - **Moeda**: As ferramentas devolvem valores já formatados (`R$ 1.234,56`), evitando reformatação pelo modelo.
- **Rationale**: SC-004 e SC-006 exigem 100%, e prompts não garantem cálculo exato.
- **Alternatives considered**: `float`, rejeitado por erro de centavo. O LLM calcular datas a partir da data injetada, rejeitado por SC-006.

## R-06 Data de referência

- **Decision**: Padrão: data atual em `America/Campo_Grande`. Pode ser fixada por `EMPORIO_DATA_REFERENCIA` ou `--data`. A data é injetada em `rules`, ferramentas e prompt.
- **Rationale**: FR-043. O fuso importa no último dia do prazo. Todos os pedidos entregues já estão fora dos prazos na data atual (o último venceu em maio de 2026), então testes e exemplos usam `2026-02-20`, com o pedido 7 no prazo e o pedido 6 fora.
- **Alternatives considered**: UTC, rejeitado porque viraria o dia 4 horas antes de Campo Grande.

## R-07 Busca de produtos

- **Decision**: Normalizar com `unidecode`, minúsculas e sem pontuação (`GD-20` vira `gd20`). Primeiro, busca exata por sequência normalizada. Depois, `rapidfuzz`. Os candidatos próximos do melhor resultado voltam como `ambiguo`, para o agente perguntar (FR-009). Categoria é texto livre, resolvido contra as categorias carregadas.
- **Rationale**: A correspondência aproximada sozinha confunde modelos parecidos, como os Takamine GC1CE e GC5CE. Limiares (ponto de partida: corte 80, empate até 5 pontos) devem ser calibrados no catálogo e medidos por SC-005. A categoria usa nome e descrição, para "violino" chegar a Cordas Orquestrais e "piano" a Teclados e Pianos, e aceita singular ("violão").
- **Alternatives considered**: Busca vetorial, excessiva para 65 produtos.

## R-08 Políticas

- **Decision**: `pdfplumber` em script executado uma vez, com um markdown revisado por tópico em `data/processed/politicas/`. A ferramenta usa um `enum` de 9 tópicos. Mapa por seção: 1 para `loja`, 2 `horario`, 3 `pagamento`, 4 `trocas_devolucoes`, 5 `frete`, 6 `promocoes`, 7 e 10 `atendimento`, 8 `garantia`, 9 `privacidade`. Substituições explícitas no script, para o texto entregue ao modelo não contradizer FR-006, FR-014 e FR-019:
  - `(67) 3321-4500` vira `(67) 3341-4444`.
  - `contato@empóriodamusica.com.br` vira `contato@emporiodamusica.com.br`.
  - A menção a "mais de 300 instrumentos" sai do texto.
  - A linha da tabela de pagamento "Até 12x sem juros, parcela mínima de R$ 100,00" passa a remeter às regras da seção 3.1.
  Testes garantem que só existe o telefone oficial e que nenhuma das frases substituídas aparece.
- **Rationale**: O manual tem 8 páginas e seções numeradas, e a seleção por tópico é determinística e testável. A extração de teste com `pdfplumber` funcionou nas 8 páginas; tabelas saem como texto e precisam de revisão.
- **Alternatives considered**: `pypdf`, com extração de tabelas mais fraca. Busca vetorial, desnecessária para este manual.

## R-09 Reclamações

- **Decision**: Ferramenta `registrar_reclamacao`, gravando em JSONL fora do Git. `contato` e `resumo` são obrigatórios. Falha de gravação volta como erro, e o agente passa o telefone, sem prometer retorno em 24 horas. `emporio reclamacoes` lista os registros para a equipe.
- **Rationale**: FR-037 e FR-038. JSONL não exige banco e é fácil de ler.
- **Alternatives considered**: SQLite, rejeitado para um único caso de escrita. Só log, rejeitado por não servir de registro consultável.

## R-10 Histórico

- **Decision**: Janela das últimas 10 trocas, sempre cortada no início de uma mensagem do cliente, para não separar chamada e resultado de ferramenta. O system prompt é refeito a cada chamada.
- **Rationale**: Provedores recusam resultados de ferramenta sem a chamada correspondente.

## R-11 Privacidade e API

- **Decision**:
  - Logs de depuração mascaram `contato`.
  - A API gera `session_id` com UUID4 e recusa ids desconhecidos, sem aceitar ids escolhidos pelo cliente.
  - A API escuta em `127.0.0.1` por padrão.
  - `data/` e `examples/` vão ao repositório público porque os dados parecem fictícios: os arquivos são de um desafio técnico e os domínios de e-mail não são reais (`jmail.com`, `coldmail.com`). O PDF diz "Documento interno": confirme se ele pode ser publicado.
- **Rationale**: Um `session_id` previsível daria acesso a um histórico com pedido já confirmado. As mensagens e os dados de pedido são enviados ao OpenRouter e ao provedor do modelo, o que é aceitável para dados fictícios, mas exige revisão de LGPD com dados reais.
- **Alternatives considered**: Autenticação na API, fora do escopo de uma API opcional local; fica como limitação no README.

## R-12 Versões das dependências

Resolução conjunta com `uv pip compile` para Python 3.11, sem conflitos: `openai` 3.42.0, `pandas` 3.1.0, `pydantic` 2.14.2, `python-dotenv` 1.2.4, `rapidfuzz` 3.14.6, `unidecode` 1.4.0, `rich` 15.0.0, `pytest` 9.2.0, `pdfplumber` 0.11.10, `fastapi` 0.162.0, `uvicorn` 0.54.0, `httpx` 0.28.1. O `uv.lock` fixa as versões. Instalação e uso em conjunto ainda não foram testados.
