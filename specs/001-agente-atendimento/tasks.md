---

description: "Lista de tarefas do agente de atendimento da Empório da Música"
---

# Tasks: Agente de Atendimento da Empório da Música

**Input**: Design documents from `/specs/001-agente-atendimento/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídos porque o input do plano pede testes `pytest` e uma suíte ponta a ponta, e os critérios de sucesso dependem deles. Escreva os testes de cada fase antes do código e confirme que falham.

**Organization**: Tarefas agrupadas por história de usuário, na ordem de prioridade da spec.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: História de usuário da tarefa (US1 a US9)

## Path Conventions

Projeto único, com `src/emporio/` e `tests/` na raiz. Os CSVs mantêm o nome original em `data/`: `desafio_tecnico_ai_eng - <tabela>.csv`. Os testes unitários usam os dados reais com `data_referencia = 2026-02-20`, salvo indicação.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicializar o projeto

- [X] T001 Inicializar o repositório com `git init` e criar `.gitignore` ignorando `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/` e `data/runtime/`
- [X] T002 Criar `pyproject.toml` com `requires-python = ">=3.11"`, dependências `openai`, `pandas`, `pydantic`, `python-dotenv`, `rapidfuzz`, `unidecode`, `rich`; grupo de desenvolvimento com `pytest` e `pdfplumber`; extra `api` com `fastapi` e `uvicorn`; script `emporio = "emporio.cli:main"`; marcador pytest `e2e`; rodar `uv sync` para gerar `uv.lock`
- [X] T003 [P] Criar `.env.example` com `OPENROUTER_API_KEY=`, `OPENROUTER_MODEL=anthropic/claude-sonnet-5.5`, `OPENROUTER_TEMPERATURE=` e `EMPORIO_DATA_REFERENCIA=`, conforme `contracts/cli.md`
- [X] T004 [P] Criar a estrutura de pacotes `src/emporio/__init__.py`, `src/emporio/data/__init__.py`, `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`, `examples/` e `scripts/`
- [X] T005 [P] Criar CSVs mínimos em `tests/fixtures/` para casos ausentes nos dados reais: produto com duas promoções ativas, produto sem preço, `specs` com JSON inválido, pedido `delivered` sem `estimated_delivery`, referência quebrada de categoria

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Dados, regras básicas, sessão, laço do agente e CLI, sem os quais nenhuma história funciona

**⚠️ CRITICAL**: Nenhuma história começa antes do fim desta fase

- [X] T006 Implementar `src/emporio/config.py`: `load_dotenv`, modelo, temperatura opcional, caminhos, limite de 6 iterações, janela de 10 trocas, e data de referência com prioridade `--data`, depois `EMPORIO_DATA_REFERENCIA`, depois hoje em `America/Campo_Grande`
- [X] T007 [P] Escrever `tests/unit/test_rules_base.py`: `formatar_brl` gera `R$ 1.234,56`; preço atual do 127 é `R$ 323,10`, do 121 `R$ 439,20`, do 90 `R$ 1.967,18` e do 94 `R$ 5.519,08`; PIX do 95 (`R$ 2.199,00`) é `R$ 2.089,05`; PIX do 127 é `R$ 323,10` com `pix_nao_acumula`; situação de 96, 113, 130 e 136
- [X] T008 Implementar em `src/emporio/rules.py` as funções puras `formatar_brl`, `preco_atual`, `calcular_pix` e `situacao_produto`, com `Decimal` e `ROUND_HALF_UP`; "`status` prevalece sobre o estoque"; PIX de 5% sobre o preço de tabela, sem acumular com promoção
- [X] T009 [P] Escrever `tests/unit/test_loader.py`: carrega 65 produtos, 9 categorias, 25 promoções, 20 pedidos, 22 itens e 50 clientes; `specs` vira dicionário; colunas faltando interrompem com a lista; avisos de JSON inválido e referência quebrada usando `tests/fixtures/`; aviso de divergência só nos pedidos 3 e 20
- [X] T010 Implementar `src/emporio/data/loader.py`: ler os CSVs, validar colunas, converter `price_brl`, `discount_percent` e `total_brl` para `Decimal` via texto, converter datas, juntar categoria, gerar `nome_normalizado` com `unidecode`, minúsculas e sem pontuação, e aplicar as regras de "Validação na inicialização" de `data-model.md`
- [X] T011 Implementar a base de `src/emporio/data/repository.py`: classe `Repository` com acesso a produto por id, categorias, promoção ativa (`is_active = 1`, maior desconto se houver várias) e promoção encerrada (`is_active = 0`, maior `promotion_id`); nenhum método público devolve `email`, `phone` ou `customer_id`
- [X] T012 [P] Implementar `src/emporio/session.py`: `SessionState` com os campos de `data-model.md`, armazenamento das mensagens do cliente e corte do histórico nas últimas 10 trocas, sempre no início de uma mensagem do cliente
- [X] T013 Implementar a base de `src/emporio/tools.py`: registro de ferramentas com modelo Pydantic, geração do schema JSON, despacho com `SessionState` e `Repository` injetados, e retorno `{"erro": "..."}` em argumento inválido ou exceção
- [X] T014 [P] Implementar `src/emporio/prompts.py`: `montar_system_prompt(data_hora)` com persona e tom do manual, fluxo de saudação a fechamento, proibição de informar preço, estoque, promoção ou prazo sem ferramenta, escopo, exigência de identificação, exibição de preço promocional com original e percentual, FR-006 e exemplos curtos de tom e recusa
- [X] T015 [P] Escrever `tests/integration/test_agent_loop.py` com cliente LLM falso: executa ferramenta e devolve resultado; resolve várias chamadas na mesma resposta; encerra com fallback e telefone após 6 iterações; falha do LLM desfaz o turno sem deixar chamada órfã; janela não separa chamada e resultado; `require_parameters` é enviado; `temperature` só é enviada se configurada
- [X] T016 Implementar `src/emporio/agent.py`: classe `Agent` com cliente `openai` injetado, `base_url` do OpenRouter, `max_retries=2`, `timeout=30`, laço de tool use, system prompt refeito a cada chamada, `extra_body={"provider": {"require_parameters": true}}`, fallback amigável com o telefone e log de ferramenta, argumentos e duração, com `contato` mascarado
- [X] T017 Implementar `src/emporio/cli.py` com `rich`: laço de conversa, `--data`, `--debug`, `sair` e `Ctrl+D`, erro de configuração em stderr com saída 1, conforme `contracts/cli.md`
- [X] T018 [P] Criar `tests/e2e/conftest.py`: pula sem `OPENROUTER_API_KEY`, marca `e2e`, fixa a data em 2026-02-20, registra ferramentas chamadas e expõe `auditar_valores`, que falha se algum `R$` da resposta não veio de ferramenta ou do cliente

**Checkpoint**: `uv run emporio` abre uma conversa, e `uv run pytest -m "not e2e"` passa

---

## Phase 3: User Story 1 - Buscar instrumentos por tipo e preço (Priority: P1) 🎯 MVP

**Goal**: Cliente filtra o catálogo por tipo e faixa de preço

**Independent Test**: Buscas por tipo e preço conferidas com o catálogo

### Tests for User Story 1

- [X] T019 [P] [US1] Escrever `tests/unit/test_busca.py`: "violões" até R$ 1000 retorna 12 no total, 10 exibidos, por menor preço, sem o 96 (sem estoque) e sem o 113 (descontinuado); `violao`, `Violões` e `violoes` resolvem a categoria 5; filtro usa `preco_atual`, então o 121 entra até R$ 450 e o 127 entra até R$ 330; a saída não contém `stock_quantity`; `sopro` e `violino` retornam `categoria_sem_itens`
- [X] T020 [P] [US1] Escrever `tests/e2e/test_us1_busca.py`: "Quais violões vocês têm até R$ 1000?" chama `buscar_produtos` e cita apenas preços de produtos válidos; categoria de sopros informa que não há itens no momento

### Implementation for User Story 1

- [X] T021 [US1] Adicionar em `src/emporio/data/repository.py` `resolver_categoria` (por nome e descrição, com singular e plural) e `buscar_produtos` (só `disponivel`, ordem de menor preço, máximo de 10, com `total_encontrado`)
- [X] T022 [US1] Adicionar a ferramenta `buscar_produtos` em `src/emporio/tools.py`, com os argumentos e a saída de `contracts/tools.md`, exceto `em_promocao` e `promocao_encontrada`, que entram na US4
- [X] T023 [US1] Em `src/emporio/prompts.py`, orientar o uso de `buscar_produtos` e o aviso de que há mais opções quando `total_encontrado > exibidos`

**Checkpoint**: A busca funciona pela CLI

---

## Phase 4: User Story 2 - Consultar preço e disponibilidade (Priority: P1)

**Goal**: Cliente consulta um produto por nome aproximado e recebe preço, situação e PIX

**Independent Test**: Perguntas sobre os produtos 95, 96, 113 e 130 e variações de nome

### Tests for User Story 2

- [X] T024 [P] [US2] Escrever `tests/unit/test_detalhes.py`: `takamine gd20`, `Takamine GD-20` e `takamin gd20` encontram o 95; `takamine` retorna `ambiguo` com os 4 candidatos; `giannini gf 3d` encontra o 96; produto inexistente retorna `nao_encontrado`; 96 tem `temporariamente_indisponivel` com alternativas disponíveis; 113 e 136 têm `fora_de_catalogo`; 130 tem `em_breve`, `pagamento` nulo e nunca aparece nas alternativas; toda alternativa é `disponivel`, da mesma categoria e ordenada por proximidade de preço
- [X] T025 [P] [US2] Escrever `tests/unit/test_variacoes_nome.py` com 20 variações de escrita (SC-005): pelo menos 18 levam ao produto certo ou a candidatos que o incluem
- [X] T026 [P] [US2] Escrever `tests/e2e/test_us2_produto.py`: "Quanto custa o Takamine GD20?" responde `R$ 2.199,00`, disponibilidade e `R$ 2.089,05` no PIX; produtos 96, 113 e 130 recebem a mensagem da sua situação

### Implementation for User Story 2

- [X] T027 [US2] Adicionar em `src/emporio/data/repository.py` a busca por referência (id, sequência normalizada exata, depois `rapidfuzz`), com resultados `encontrado`, `ambiguo` (até 5) e `nao_encontrado`; calibrar os limiares (ponto de partida: corte 80, empate até 5) até T025 passar
- [X] T028 [US2] Adicionar em `src/emporio/data/repository.py` `alternativas`: até 3 produtos `disponivel` da mesma categoria, com preço mais próximo
- [X] T029 [US2] Adicionar a ferramenta `detalhes_produto` em `src/emporio/tools.py`, conforme `contracts/tools.md`, inicialmente com `pagamento.pix` e `pix_nao_acumula`; `parcelas` e `promocao_encerrada` entram na US4
- [X] T030 [US2] Em `src/emporio/prompts.py`, orientar a resposta por `situacao` e a pergunta de confirmação quando `resultado` for `ambiguo`

**Checkpoint**: US1 e US2 funcionam de forma independente

---

## Phase 5: User Story 3 - Obter informações gerais da loja (Priority: P1)

**Goal**: Cliente recebe endereço, telefone, horário, pagamento, frete e garantia do manual

**Independent Test**: Cada informação comparada com o manual

### Tests for User Story 3

- [X] T031 [P] [US3] Escrever `tests/unit/test_policies.py`: os 9 tópicos existem e não estão vazios; nenhum contém `3321-4500`, `empóriodamusica` ou `mais de 300`; `(67) 3341-4444` e `Rua 14 de Maio, 3200` estão em `loja`; `pagamento` não diz que toda compra parcelada exige R$ 100; tópico inválido retorna erro
- [X] T032 [P] [US3] Escrever `tests/e2e/test_us3_loja.py`: "Qual o endereço da loja?" chama só `consultar_politica`; horário, frete e garantia coincidem com o manual; frete por CEP não informa valor exato

### Implementation for User Story 3

- [X] T033 [US3] Implementar `scripts/extract_policies.py` com `pdfplumber`, separando por seção conforme o mapa de R-08 e aplicando as 4 substituições explícitas de R-08
- [X] T034 [US3] Rodar `scripts/extract_policies.py`, revisar as tabelas e versionar os 9 arquivos em `data/processed/politicas/`
- [X] T035 [US3] Implementar `src/emporio/policies.py`: carregar os 9 arquivos e falhar na inicialização se algum faltar ou estiver vazio
- [X] T036 [US3] Adicionar a ferramenta `consultar_politica` em `src/emporio/tools.py`, com `enum` de tópicos
- [X] T037 [US3] Em `src/emporio/prompts.py`, mapear perguntas para tópicos e exigir `consultar_politica` para dados da loja, sem usar ferramentas de produto

**Checkpoint**: MVP completo: produtos e informações da loja

---

## Phase 6: User Story 4 - Consultar promoção e pagamento (Priority: P2)

**Goal**: Cliente vê promoções, valor no PIX e parcelas

**Independent Test**: Valores de produtos com e sem promoção conferidos com as regras do manual

**Depende de**: US1 e US2

### Tests for User Story 4

- [X] T038 [P] [US4] Escrever `tests/unit/test_parcelamento.py`, com ao menos 20 casos (SC-004): R$ 2.199,00 permite 12x; R$ 323,10 permite 4x; R$ 439,20 permite 5x; R$ 159,90 permite 3x; R$ 599,90 permite 6x; R$ 800,00 permite 8x; R$ 90,00 permite 1x; a comparação usa o valor antes de arredondar; 2x e 3x exigem R$ 50
- [X] T039 [P] [US4] Escrever `tests/unit/test_promocoes.py`: 4 produtos com promoção ativa; fixture com duas ativas usa o maior desconto; 95 sem promoção ativa traz encerrada `Oferta Especial`; 96 traz a de `promotion_id` 22; `em_promocao` lista 90, 94, 121 e 127; "Black Friday" retorna `ativa` falso
- [X] T040 [P] [US4] Escrever `tests/e2e/test_us4_pagamento.py`: preço promocional aparece com original e percentual; PIX não acumula e o agente explica; parcelamento impossível indica o máximo; promoção encerrada é informada com o preço atual

### Implementation for User Story 4

- [X] T041 [US4] Adicionar `tabela_parcelas` em `src/emporio/rules.py`: "1x sem mínimo; 2x e 3x com mínimo de R$ 50; 4x a 6x com mínimo de R$ 80; 7x a 12x com mínimo de R$ 100", sobre o preço atual
- [X] T042 [US4] Completar `detalhes_produto` em `src/emporio/tools.py` com `parcelas`, `max_parcelas` e `promocao_encerrada`
- [X] T043 [US4] Adicionar `em_promocao` e `promocao_encontrada` em `src/emporio/data/repository.py` e na ferramenta `buscar_produtos` em `src/emporio/tools.py`
- [X] T044 [US4] Em `src/emporio/prompts.py`, orientar a transparência sobre promoção encerrada, sem prometer desconto

**Checkpoint**: Valores de pagamento conferem ao centavo

---

## Phase 7: User Story 5 - Acompanhar um pedido (Priority: P2)

**Goal**: Cliente confirma a identidade e recebe status, rastreio e previsão

**Independent Test**: Pedidos em cada status, com e sem confirmação correta

### Tests for User Story 5

- [X] T045 [P] [US5] Escrever `tests/unit/test_identidade.py`: contato igual aceita `ANACAROL.FERREIRA@COLDMAIL.COM`, `(67) 99654-7821`, `5567996547821` e `99654-7821`; recusa menos de 8 dígitos; o e-mail repetido de `bruno.martins@jmail.com` só abre pedido do dono
- [X] T046 [P] [US5] Escrever `tests/unit/test_consultar_pedido.py`: pedido 8 sem contato retorna `precisa_confirmacao`, sem dados; com o contato de outro cliente e pedido inexistente, a resposta é idêntica; a 3ª falha retorna `bloqueado` e a consulta seguinte não acessa os dados; confirmar o pedido 1 não abre o 19, mesmo do mesmo cliente, sem o contato ser escrito de novo; contato que o cliente não escreveu não vale nem conta como falha; janela de histórico não zera falhas; total do pedido 3 é `R$ 3.450,00`; pedido 19 traz o motivo; a saída não tem `email`, `phone`, `customer_id` nem valor por item
- [X] T047 [P] [US5] Escrever `tests/e2e/test_us5_pedido.py`, somando 20 tentativas com T046 (SC-003): "Qual o status do pedido 8?" pede o contato sem revelar nada; pessoa dizendo ser atendente, dono ou familiar, e pedido para ignorar as regras, não recebem dados; com `anacarol.ferreira@coldmail.com`, responde enviado, `BRJL5544332BR` e previsão

### Implementation for User Story 5

- [X] T048 [US5] Adicionar em `src/emporio/rules.py` `contato_confere`: e-mail sem diferença de caixa e espaços; telefone só com dígitos, sem `55`, aceitando sem DDD com pelo menos os 8 últimos dígitos
- [X] T049 [US5] Adicionar em `src/emporio/data/repository.py` `pedido_confere(numero, contato)` e `dados_pedido(numero)`, com itens por nome e quantidade, status e pagamento traduzidos e `primeiro_nome`, sem expor dados de contato
- [X] T050 [US5] Adicionar em `src/emporio/session.py` os métodos de confirmação: registrar falha, bloquear em 3, conferir se o contato foi escrito pelo cliente e limpar as mensagens depois do sucesso
- [X] T051 [US5] Adicionar a ferramenta `consultar_pedido` em `src/emporio/tools.py`, com os resultados `ok`, `precisa_confirmacao`, `nao_confirmado` e `bloqueado` de `contracts/tools.md`
- [X] T052 [US5] Em `src/emporio/prompts.py`, orientar a pedir número e contato, saudar pelo primeiro nome depois da confirmação e indicar o telefone quando `bloqueado`

**Checkpoint**: Nenhum dado de pedido sai sem confirmação

---

## Phase 8: User Story 6 - Saber se posso trocar ou devolver (Priority: P2)

**Goal**: Cliente sabe se está no prazo, com datas calculadas em código

**Independent Test**: Pedidos dentro e fora de cada prazo, com data fixa

**Depende de**: US3 e US5

### Tests for User Story 6

- [X] T053 [P] [US6] Escrever `tests/unit/test_prazos.py` (SC-006): pedido 7 com arrependimento e troca até 2026-02-24 (no prazo nesse dia, encerrado em 02-25), defeito até 2026-03-05 e garantia legal até 2026-05-18; em 2026-02-20, pedido 6 com arrependimento e defeito encerrados; pedidos 8 e 9 com `nao_iniciado`; pedidos 17 a 20 com `nao_se_aplica`; fixture sem `estimated_delivery` com `indeterminado` nos prazos que dependem dela e defeito ainda calculado
- [X] T054 [P] [US6] Escrever `tests/e2e/test_us6_trocas.py`: "Me arrependi da compra, posso devolver?" pede pedido e contato, depois responde no prazo para o pedido 7 e fora do prazo para o 6, com a data; sem pedido, explica a regra geral; prazo `indeterminado` encaminha para a equipe

### Implementation for User Story 6

- [X] T055 [US6] Adicionar `calcular_prazos` em `src/emporio/rules.py`: arrependimento e troca em 7 dias e garantia legal em 90, contados de `estimated_delivery`; defeito em 30, contado de `order_date`; último dia incluído; `situacao` por status do pedido
- [X] T056 [US6] Incluir `prazos` na saída de `consultar_pedido` em `src/emporio/tools.py`, conforme `contracts/tools.md`
- [X] T057 [US6] Em `src/emporio/prompts.py`, orientar a usar `prazos`, sem calcular datas; combinar com `consultar_politica`; perguntar sobre personalização e "venda final" e indicar garantia depois dos 30 dias

**Checkpoint**: Conclusões de prazo vêm do código

---

## Phase 9: User Story 7 - Fazer perguntas de seguimento (Priority: P2)

**Goal**: Conversa natural, sem repetir o contexto

**Independent Test**: Segunda pergunta que só faz sentido com a primeira

**Depende de**: US2

- [X] T058 [P] [US7] Escrever `tests/integration/test_sessoes.py`: duas sessões não compartilham histórico nem confirmações
- [X] T059 [P] [US7] Escrever `tests/e2e/test_us7_seguimento.py` com 10 conversas (SC-007): "e no PIX?" responde sobre o mesmo produto; "tem outro parecido?" usa `alternativas`, só com disponíveis
- [X] T060 [US7] Ajustar `src/emporio/prompts.py` e, se T058 falhar, `src/emporio/agent.py`, para resolver referências da conversa e chamar a ferramenta de novo quando o resultado sair da janela

**Checkpoint**: Seguimentos funcionam sem repetir contexto

---

## Phase 10: User Story 8 - Receber redirecionamento educado (Priority: P3)

**Goal**: Agente mantém o escopo com educação

**Independent Test**: Pedidos de acessórios, assuntos alheios e ações fora de escopo

- [X] T061 [P] [US8] Escrever `tests/e2e/test_us8_escopo.py`: "Vocês vendem cordas de guitarra?" redireciona; "cordas" sozinho esclarece se é acessório ou instrumento; receita de bolo é recusada; fechar venda, cancelar pedido e calcular frete por CEP são recusados com orientação; nenhuma loja parceira é inventada
- [X] T062 [US8] Completar em `src/emporio/prompts.py` as regras e exemplos de escopo: lista de acessórios do FR-034, recusa educada, ações proibidas do FR-040 e resposta em português para outros idiomas

**Checkpoint**: Cenários de escopo passam

---

## Phase 11: User Story 9 - Registrar reclamação ou falar com a equipe (Priority: P3)

**Goal**: Reclamação registrada e encaminhamento sem improviso

**Independent Test**: Reclamação registrada e consultada; pergunta fora do manual encaminhada

- [X] T063 [P] [US9] Escrever `tests/unit/test_complaints.py` com diretório temporário: grava campos de `data-model.md`; "`resumo` obrigatório, não vazio" e "`contato` obrigatório, não vazio"; falha de escrita retorna `registrada` falso; listagem da mais recente para a mais antiga
- [X] T064 [P] [US9] Escrever `tests/e2e/test_us9_reclamacao.py`: reclamação recebe empatia, pede contato antes de registrar e informa 24 horas úteis; pergunta não coberta encaminha para o telefone oficial; às 20h, informa a volta da equipe às 9h do dia seguinte
- [X] T065 [US9] Implementar `src/emporio/complaints.py`, gravando em `data/runtime/reclamacoes.jsonl`
- [X] T066 [US9] Adicionar a ferramenta `registrar_reclamacao` em `src/emporio/tools.py`, conforme `contracts/tools.md`
- [X] T067 [US9] Adicionar o subcomando `reclamacoes` em `src/emporio/cli.py`, conforme `contracts/cli.md`
- [X] T068 [US9] Em `src/emporio/prompts.py`, orientar a pedir contato antes de registrar, só prometer 24 horas úteis com `registrada` verdadeiro, encaminhar sem improviso (FR-039) e, com a data e hora injetadas, informar a volta da equipe fora do horário (FR-047)

**Checkpoint**: Todas as histórias funcionam

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: API opcional, medição dos critérios e entregáveis

- [X] T069 [P] Escrever `tests/integration/test_api.py` com `httpx` e LLM falso: sem `session_id` cria sessão; id desconhecido retorna 404; mensagem vazia retorna 422; resposta não expõe chamadas de ferramenta
- [X] T070 Implementar `src/emporio/api.py` com FastAPI: `POST /chat` e `GET /health`, conforme `contracts/http-api.md`, com `session_id` em UUID4 gerado pelo servidor, trava por sessão e `127.0.0.1` como padrão documentado
- [X] T071 [P] Escrever `tests/unit/test_logs.py`: `--debug` mascara `contato` e não registra e-mail nem telefone
- [X] T072 [P] Escrever `tests/e2e/test_exatidao.py` com 30 perguntas (SC-002) e o conjunto de perguntas recorrentes (SC-008), aplicando `auditar_valores` e medindo o percentil 95 de duração (SC-009)
- [ ] T073 Rodar `uv run pytest -m e2e` três vezes com `anthropic/claude-sonnet-5.5` e `anthropic/claude-haiku-5.5`, definir o modelo padrão em `src/emporio/config.py` e `.env.example`, e registrar exatidão, custo e tempo no `README.md`
- [X] T074 Gerar pela CLI de 3 a 5 conversas em `examples/`, com `--data 2026-02-20`: ao menos uma com o pedido 7 e prazo de arrependimento, e uma com promoção e parcelas
- [X] T075 Escrever `README.md`: instalação com `uv sync`, `.env`, execução; justificativas (OpenRouter, function calling, sem framework, manual por seção); `--data` e o motivo; suposições; limitações (promoções sem data, itens sem preço pago, pedidos 3, 20, 9, 16 e 18, bloqueio por sessão, API sem autenticação, envio de dados ao provedor); próximos passos; uso de assistentes de IA
- [X] T076 Executar `specs/001-agente-atendimento/quickstart.md` do início ao fim e corrigir divergências em `README.md`
- [ ] T077 Solicitar a revisão de tom de 20 respostas (SC-010) e o teste do README por uma pessoa de fora (SC-011), registrando o resultado em `README.md`
- [ ] T078 Conferir com `git log` e `git status` que o histórico é real e que `.env` e `data/runtime/` não estão versionados; só publicar o repositório depois da confirmação do responsável, incluindo a do PDF marcado como documento interno

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: Sem dependências
- **Foundational (Fase 2)**: Depende do Setup e bloqueia todas as histórias
- **Histórias (Fases 3 a 11)**: Dependem da Fase 2
- **Polish (Fase 12)**: Depende das histórias desejadas

### User Story Dependencies

- **US1 (P1)**: Só da Fase 2
- **US2 (P1)**: Só da Fase 2
- **US3 (P1)**: Só da Fase 2
- **US4 (P2)**: Depende de US1 e US2, que recebe as ferramentas a completar
- **US5 (P2)**: Só da Fase 2
- **US6 (P2)**: Depende de US3 e US5
- **US7 (P2)**: Depende de US2
- **US8 (P3)**: Só da Fase 2
- **US9 (P3)**: Só da Fase 2

### Within Each User Story

- Testes primeiro, e devem falhar antes da implementação
- `rules.py` e `repository.py`, depois `tools.py`, depois `prompts.py`
- `prompts.py`, `tools.py`, `rules.py` e `repository.py` são compartilhados, portanto tarefas de histórias diferentes nesses arquivos não rodam ao mesmo tempo

### Parallel Opportunities

- Setup: T003, T004 e T005
- Fundação: T007, T009, T012, T014, T015 e T018
- Testes de cada história, marcados com [P]
- Polish: T069, T071 e T072

---

## Parallel Example: User Story 1

```bash
# Escrever os testes da história ao mesmo tempo:
Task: "Escrever tests/unit/test_busca.py"
Task: "Escrever tests/e2e/test_us1_busca.py"

# Depois, em sequência, por tocarem módulos dependentes:
Task: "Adicionar buscar_produtos em src/emporio/data/repository.py"
Task: "Adicionar a ferramenta buscar_produtos em src/emporio/tools.py"
```

---

## Implementation Strategy

### MVP First

1. Concluir as Fases 1 e 2
2. Concluir as Fases 3, 4 e 5 (US1, US2 e US3)
3. **Parar e validar** com `uv run pytest -m "not e2e"` e as linhas de produto e loja do `quickstart.md`

### Incremental Delivery

1. US1 + US2 + US3: catálogo e dados da loja (MVP)
2. US4: promoções e pagamento
3. US5 + US6: pedidos e trocas, com a confirmação de identidade
4. US7 + US8: conversa natural e escopo
5. US9: reclamações e encaminhamento
6. Polish: API, medições, exemplos e README

### Parallel Team Strategy

Depois da Fase 2, uma pessoa pode ficar com catálogo (US1, US2, US4), outra com pedidos (US5, US6) e outra com loja e atendimento (US3, US8, US9), coordenando as alterações em `tools.py` e `prompts.py`.

---

## Notes

- [P] = arquivos diferentes, sem dependência pendente
- Faça commits por tarefa ou grupo lógico, para formar um histórico real
- As tarefas `e2e` exigem `OPENROUTER_API_KEY` e geram custo
- T077 depende de pessoas, e T078 depende de confirmação antes de publicar
- Pare em cada checkpoint para validar a história
