# Contrato: Interface de Linha de Comando

## `emporio` (conversa)

```text
uv run emporio [--data AAAA-MM-DD] [--debug]
```

| Opção | Efeito |
|-------|--------|
| `--data` | Fixa a data de referência; tem prioridade sobre `EMPORIO_DATA_REFERENCIA` |
| `--debug` | Mostra ferramenta, argumentos e duração em stderr, com `contato` mascarado |

- Cada execução é uma sessão nova.
- Ao iniciar, valida configuração e dados. Em erro, informa o motivo em stderr e sai com código 1.
- `sair` ou `Ctrl+D` encerram com código 0.
- Falha do LLM mostra mensagem amigável com o telefone da loja, e a conversa continua.

## `emporio reclamacoes` (equipe)

```text
uv run emporio reclamacoes
```

Lista as reclamações registradas, da mais recente para a mais antiga. Sem registros, informa que não há nenhuma.

## Variáveis de ambiente

| Variável | Obrigatória | Padrão |
|----------|-------------|--------|
| `OPENROUTER_API_KEY` | Sim, para conversar | Nenhum |
| `OPENROUTER_MODEL` | Não | `anthropic/claude-haiku-5.5` |
| `OPENROUTER_TEMPERATURE` | Não | Não enviada |
| `EMPORIO_DATA_REFERENCIA` | Não | Data atual em `America/Campo_Grande` |
