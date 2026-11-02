# Data Model: Dashboard de Demonstração do Chat

## Conversa

Um arquivo `data/runtime/conversas/<id>.json`. O `id` é o mesmo da sessão, um UUID.

| Campo | Tipo | Regra |
|---|---|---|
| `id` | texto | UUID. Qualquer outro formato é recusado antes de tocar no disco |
| `titulo` | texto | Primeira mensagem do cliente, cortada em 60 caracteres |
| `iniciada_em` | data e hora ISO | Relógio real, no fuso de Campo Grande |
| `atualizada_em` | data e hora ISO | Horário da última mensagem; ordena a lista |
| `mensagens` | lista de Mensagem | Todas, sem o corte da janela enviada ao modelo |

`somente_leitura` não é gravado. Vale `true` quando o `id` não está nas sessões em memória.

## Mensagem

| Campo | Tipo | Regra |
|---|---|---|
| `autor` | `cliente` ou `agente` | |
| `texto` | texto | Sem alteração, inclusive a mensagem de contingência |
| `momento` | data e hora ISO | |
| `tempo_ms` | inteiro | Só no agente |
| `consultas` | lista de Consulta | Só no agente; lista vazia significa nenhuma consulta |

## Consulta

| Campo | Tipo | Regra |
|---|---|---|
| `nome` | texto | Nome da ferramenta |
| `parametros` | texto | Saída de `mascarar_argumentos` |
| `duracao_ms` | decimal | |

O resultado da ferramenta não é gravado (FR-021).

## Indicadores

Calculados a cada leitura, sem registro próprio.

| Campo | Cálculo |
|---|---|
| `conversas` | Conversas legíveis |
| `mensagens_cliente` | Mensagens com autor `cliente` |
| `tempo_medio_ms` | Média de `tempo_ms` das mensagens do agente; 0 sem mensagens |
| `consultas_mais_usadas` | Até 3 pares de nome e total, do maior para o menor |

## Mudança em `SessionState`

Novo campo `consultas_turno: list[dict]`, limpo no início de cada `responder`. Fica fora de `mensagens`, portanto não vai ao modelo.

## Transições

```text
(sem arquivo) → ativa            primeira resposta gravada
ativa → ativa                    nova troca
ativa → somente leitura          reinício da aplicação
ativa ou somente leitura → (sem arquivo)   apagada pela pessoa
```

Uma conversa só é gravada depois da primeira resposta, então não há conversas vazias. Cliente e agente são gravados juntos, e uma resposta interrompida por reinício não deixa rastro.
