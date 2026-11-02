# Implementation Plan: Dashboard de Demonstração do Chat

**Branch**: `002-dashboard-demo` (ainda não criada; o trabalho está em `001-agente-atendimento`) | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-dashboard-demo/spec.md`, com a orientação "pode usar que for de mais fácil e simples".

## Summary

Uma única página HTML, com CSS e JavaScript no próprio arquivo, servida pela API que já existe. O histórico fica em um arquivo JSON por conversa, em `data/runtime/conversas/`. Nenhuma dependência nova, nenhuma etapa de build e nenhum banco de dados.

O agente muda pouco: passa a anotar as consultas de cada turno. `POST /chat` mantém o contrato e grava o histórico. Depois de cada resposta, a página recarrega a conversa e a lista.

## Technical Context

**Language/Version**: Python 3.11+ e JavaScript puro, sem transpilação

**Primary Dependencies**: FastAPI e uvicorn (extra `api`, já existente). Nenhuma nova

**Storage**: Arquivos JSON em `data/runtime/conversas/<id>.json`, ignorados pelo Git

**Testing**: pytest com `TestClient` e LLM falso. A página é conferida no navegador, pelo [quickstart](quickstart.md)

**Target Platform**: Computador local, em navegador atual

**Project Type**: Serviço web local com uma página

**Performance Goals**: Abrir conversa de 100 mensagens em menos de 1 s e carregar a página com 200 conversas em menos de 2 s (SC-004)

**Constraints**: Página sem recursos externos (FR-028), `POST /chat` sem mudança de contrato (FR-027) e nenhum dado pessoal nos parâmetros exibidos (FR-020)

**Scale/Scope**: Uma pessoa por vez e centenas de conversas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` ainda é o modelo em branco, sem princípios ratificados. Não há portões formais. Valem os critérios já adotados no projeto:

| Critério | Antes do desenho | Depois do desenho |
|---|---|---|
| Regra de negócio só em Python determinístico | Passa: a página só exibe | Passa |
| Modelo sem acesso ao estado da sessão | Passa: só `mensagens` vai ao LLM | Passa: `consultas_turno` não vai |
| Testável sem rede | Passa | Passa: `Historico` recebe a pasta |
| Sem credenciais ou dados gerados no Git | Passa | Passa: `data/runtime/` já é ignorada |
| Simples e explicável | Passa | Passa: 1 arquivo Python e 1 HTML novos |

## Project Structure

### Documentation (this feature)

```text
specs/002-dashboard-demo/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/api.md
├── checklists/requirements.md
└── tasks.md             # criado por /speckit-tasks
```

### Source Code (repository root)

```text
src/emporio/
├── historico.py         # novo: conversas em JSON e indicadores
├── static/dashboard.html # novo: a página inteira
├── api.py               # novas rotas; /chat grava o histórico
├── agent.py             # anota as consultas; máscara de e-mail e telefone
├── session.py           # campo consultas_turno
└── config.py            # PASTA_CONVERSAS

tests/
├── unit/test_historico.py       # novo
├── unit/test_logs.py            # máscara ampliada
├── integration/test_dashboard.py # novo
└── integration/test_api.py      # fixtures passam pasta temporária
```

**Structure Decision**: Projeto único. O código entra em `src/emporio/`, sem pasta de frontend, porque a página é um arquivo só.

## Complexity Tracking

Sem violações a justificar.
