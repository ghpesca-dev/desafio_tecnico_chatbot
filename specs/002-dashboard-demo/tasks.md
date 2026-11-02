# Tasks: Dashboard de Demonstração do Chat

**Input**: Design documents from `specs/002-dashboard-demo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Pedidos no plano: pytest sem rede. A página é conferida pelo roteiro do quickstart.

**Organization**: Tarefas agrupadas por história de usuário.

## Phase 1: Setup

- [X] T001 Adicionar `PASTA_CONVERSAS = PASTA_DADOS / "runtime" / "conversas"` em src/emporio/config.py
- [X] T002 Passar uma pasta temporária aos fixtures de `criar_app` em tests/integration/test_api.py, para os testes não gravarem em `data/runtime/`

---

## Phase 2: Foundational

**Purpose**: Histórico e captura de consultas, usados por todas as histórias.

- [X] T003 [P] Escrever testes de gravação, leitura, ordem, corte do título em 60 caracteres, `id` inválido, arquivo danificado, pasta ausente, remoção e indicadores em tests/unit/test_historico.py
- [X] T004 [P] Escrever testes de `consultas_turno` e de máscara de e-mail e de 8 ou mais dígitos em texto livre em tests/unit/test_logs.py
- [X] T005 Implementar `Historico` em src/emporio/historico.py: um JSON por conversa, gravação com arquivo temporário e `os.replace`, `id` validado como UUID antes de tocar no disco, resultado de ferramenta nunca gravado
- [X] T006 Adicionar `consultas_turno: list[dict]` em src/emporio/session.py
- [X] T007 Limpar e preencher `consultas_turno` em `Agent.responder` e `_executar_chamadas`, ampliar `mascarar_argumentos` e expor a data de referência em src/emporio/agent.py

**Checkpoint**: Base pronta; `POST /chat` ainda sem histórico.

---

## Phase 3: User Story 1 - Conversar pelo navegador (Priority: P1) 🎯 MVP

**Goal**: Conversar com o agente numa página.

**Independent Test**: Abrir a página e trocar mensagens, inclusive um seguimento.

- [X] T008 [US1] Escrever testes de `GET /`, de `POST /chat` gravando o histórico, de contrato inalterado e de falha de gravação sem afetar a resposta em tests/integration/test_dashboard.py
- [X] T009 [US1] Escrever teste de que a página não usa `innerHTML` nem URLs externas em tests/integration/test_dashboard.py
- [X] T010 [US1] Servir `GET /` e gravar a troca em `POST /chat` em src/emporio/api.py
- [X] T011 [US1] Criar a página com conversa, indicador de espera, envio bloqueado durante a resposta, renderizador por `textContent` e aviso de demonstração em src/emporio/static/dashboard.html

**Checkpoint**: Demonstração possível sem o terminal.

---

## Phase 4: User Story 2 - Histórico de conversas (Priority: P1)

**Goal**: Listar, abrir, alternar, começar e apagar conversas.

**Independent Test**: Criar duas conversas, alternar, reiniciar e confirmar que continuam na lista.

- [X] T012 [US2] Escrever testes de lista, abertura, somente leitura após recriar o app, remoção, `id` inválido e remoção durante mensagem na fila em tests/integration/test_dashboard.py
- [X] T013 [US2] Implementar `GET /conversas`, `GET /conversas/{id}` e `DELETE /conversas/{id}`, com `apagada` em `Sessao`, em src/emporio/api.py
- [X] T014 [US2] Adicionar lista lateral, nova conversa, alternância, somente leitura, apagar com confirmação e layout estreito em src/emporio/static/dashboard.html

**Checkpoint**: Histórico completo.

---

## Phase 5: User Story 3 - Como o agente chegou à resposta (Priority: P2)

**Goal**: Mostrar consultas e tempo de cada resposta.

**Independent Test**: Comparar as consultas mostradas para perguntas de preço, política e fora do tema.

- [X] T015 [US3] Escrever teste de consultas com contato mascarado, tempo e ausência do resultado bruto em `GET /conversas/{id}` em tests/integration/test_dashboard.py
- [X] T016 [US3] Mostrar consultas, parâmetros, tempo e a indicação de nenhuma consulta em src/emporio/static/dashboard.html

**Checkpoint**: Transparência visível, ao vivo e no histórico.

---

## Phase 6: User Story 4 - Números da demonstração (Priority: P3)

**Goal**: Indicadores no topo.

**Independent Test**: Conferir os números contra uma contagem manual.

- [X] T017 [US4] Escrever teste de indicadores e `data_referencia` em `GET /conversas` em tests/integration/test_dashboard.py
- [X] T018 [US4] Mostrar indicadores e data fixada, atualizando após cada resposta, em src/emporio/static/dashboard.html

---

## Phase 7: User Story 5 - Perguntas de exemplo (Priority: P3)

**Goal**: Exemplos prontos numa conversa vazia.

**Independent Test**: Usar cada exemplo numa conversa nova.

- [X] T019 [US5] Adicionar exemplos de produto, promoção, pedido, política e fora de escopo, sem dados de cliente, em src/emporio/static/dashboard.html

---

## Phase 8: Polish

- [X] T020 Documentar o dashboard, a data de referência e as limitações em README.md
- [X] T021 Rodar `uv run pytest` e confirmar que nada foi gravado em `data/runtime/`
- [X] T022 Executar o roteiro de specs/002-dashboard-demo/quickstart.md no navegador

---

## Dependencies & Execution Order

- Setup → Foundational → US1 → US2 → US3, US4 e US5.
- US3, US4 e US5 mexem no mesmo HTML, então seguem em sequência.
- Dentro de cada fase, testes antes da implementação.

### Parallel Example

```text
T003 tests/unit/test_historico.py
T004 tests/unit/test_logs.py
```


## Implementation Strategy

- **MVP**: Fases 1 a 3.
- **Pedido central**: Fase 4, o histórico.
- **Incremental**: Fases 5 a 7 acrescentam sem alterar o que já funciona.
