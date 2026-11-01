# Implementation Plan: Agente de Atendimento da Empório da Música

**Branch**: `001-agente-atendimento` (nome lógico; o projeto ainda não é um repositório Git) | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-agente-atendimento/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Agente único de atendimento por texto para a Empório da Música, com function calling e laço de tool use escrito à mão, sem framework de agentes. O LLM interpreta a mensagem, escolhe a ferramenta e redige a resposta. Preço, estoque, promoção, pedido, prazo e identidade vêm sempre de código Python determinístico e testado. As fontes são os CSVs da operação, carregados em memória, e o manual em PDF, convertido uma vez em markdown por seção. O uso é por CLI, com API HTTP opcional.

O plano segue o input do usuário, com sete ajustes exigidos pela spec ou pela verificação feita na pesquisa. Eles estão em [Desvios do input](#desvios-do-input).

## Technical Context

**Language/Version**: Python 3.11+ (`requires-python = ">=3.11"`), gerenciado com `uv`

**Primary Dependencies**: `openai` (SDK apontando para o OpenRouter), `pandas`, `pydantic`, `python-dotenv`, `rapidfuzz`, `unidecode`, `rich`. Só para pré-processamento: `pdfplumber`. Extra `api`: `fastapi`, `uvicorn`. Versões em [research.md](research.md#r-12-versões-das-dependências)

**Storage**: Sem banco. CSVs e markdown versionados, lidos em memória; sessões em memória; reclamações em arquivo JSONL fora do Git (`data/runtime/reclamacoes.jsonl`)

**Testing**: `pytest`. Unitários sem rede, testes do laço com LLM falso e suíte ponta a ponta marcada com `e2e`, que só roda com `OPENROUTER_API_KEY`

**Target Platform**: Terminal em Linux, macOS ou WSL; API opcional em servidor local

**Project Type**: CLI com biblioteca Python (`src/emporio`) e serviço HTTP opcional

**Performance Goals**: 95% das respostas em até 10 s (SC-009). Consultas locais em menos de 100 ms, para que o tempo fique dominado pelas chamadas ao LLM. Ainda não medido: exige chave configurada

**Constraints**: Nenhum dado de negócio redigido sem ferramenta (FR-003); identidade verificada em código (FR-022); valores em `Decimal` ao centavo (FR-020); dados de contato fora do contexto do LLM e dos logs; limite de 6 iterações por turno

**Scale/Scope**: 65 produtos, 9 tópicos de política, 5 ferramentas, uso de demonstração com poucas sessões simultâneas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` ainda é o modelo vazio, sem princípios ratificados. Portanto, não há gates formais a avaliar, e não inventei princípios em nome do projeto. **Resultado: sem violações, antes e depois do design, por ausência de gates.**

Na falta deles, usei como verificação as prioridades declaradas no input. São critérios de trabalho deste plano, não uma constitution.

| Verificação | Antes do design | Depois do design |
|-------------|-----------------|------------------|
| Dados de negócio vêm de código determinístico | OK | OK: `rules.py` e ferramentas; prazos deixaram de depender do LLM (R-05) |
| Regras sensíveis não dependem do prompt | Lacuna: FR-022, FR-025 e FR-026 | OK: estado de sessão em código, fora do alcance do modelo (R-04) |
| Arquitetura simples e explicável | OK | OK: um agente e 5 ferramentas, sem framework |
| Código fácil de testar | OK | OK: regras puras, data e LLM injetados |

## Desvios do input

| # | Input sugerido | Plano | Motivo |
|---|----------------|-------|--------|
| 1 | 4 ferramentas | 5, com `registrar_reclamacao` | FR-037 e FR-038 exigem um registro que dure além da sessão |
| 2 | `buscar_produtos` com "incluir indisponíveis" | Parâmetro removido; `em_promocao` adicionado | FR-008 proíbe mostrar indisponíveis na busca; "tem promoção?" não tinha caminho |
| 3 | Busca retorna estoque | Retorna apenas `disponivel` | FR-013: o modelo não deve receber a quantidade exata |
| 4 | Data injetada para o cálculo de prazos | Python calcula os prazos; a data continua no prompt | FR-031, FR-032 e SC-006 pedem 100% de acerto, e prazo é regra de negócio |
| 5 | `customers` nunca exposto ao modelo | Mantido, exceto `primeiro_nome` após a confirmação | O fluxo do manual pede saudação pelo nome |
| 6 | Temperatura de 0,2 a 0,3 | Opcional, desligada por padrão | Os modelos Claude e GPT recentes não listam `temperature` no OpenRouter (R-02) |
| 7 | Alternativas só se indisponível | Sempre até 3 alternativas | US7 ("tem outro parecido?") vale também para produto disponível |

**Revisão após receber os dados (2026-11-01)**: A versão anterior deste plano exigia vigência por data nas promoções. O CSV não tem datas, então volta a valer `is_active = 1`, como no input. Veja [R-01](research.md#r-01-dados-de-origem-conferidos).

## Project Structure

### Documentation (this feature)

```text
specs/001-agente-atendimento/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   ├── tools.md         # Ferramentas expostas ao LLM
│   ├── cli.md           # Interface de linha de comando
│   └── http-api.md      # API opcional
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
data/                        # CSVs e PDF originais
├── processed/politicas/     # Um markdown por tópico, versionado
└── runtime/                 # Reclamações; fora do Git
src/emporio/
├── config.py                # Variáveis de ambiente e parâmetros
├── data/
│   ├── loader.py            # Leitura, validação e enriquecimento dos CSVs
│   └── repository.py        # Consultas a produtos, promoções e pedidos
├── rules.py                 # Regras puras: preço, PIX, parcelas, prazos, contato
├── session.py               # Estado da sessão: confirmações e falhas
├── complaints.py            # Gravação e leitura de reclamações
├── policies.py              # Carga das seções do manual
├── tools.py                 # Ferramentas, schemas e despacho
├── prompts.py               # System prompt da persona
├── agent.py                 # Laço de tool use e histórico
├── cli.py                   # Interface de linha de comando
└── api.py                   # FastAPI (extra opcional)
scripts/extract_policies.py  # Conversão única do PDF
tests/
├── fixtures/                # CSVs pequenos com datas fixas
├── unit/                    # Regras, loader, busca, sessão, ferramentas
├── integration/             # Laço do agente com LLM falso
└── e2e/                     # Cenários com LLM real, marcador `e2e`
examples/                    # De 3 a 5 conversas em .md
pyproject.toml, uv.lock, .env.example, .gitignore, README.md
```

**Structure Decision**: Projeto único, com a estrutura do input e três módulos a mais: `rules.py` (regras puras, sem dependências, testáveis isoladamente), `session.py` (estado que o modelo não controla) e `complaints.py` (gravação exigida pelo FR-038).

## Complexity Tracking

Sem violações de constitution a justificar: não há princípios ratificados.
