# Contrato: API HTTP (opcional)

Instalada com o extra `api`. Escuta em `127.0.0.1` por padrão e não tem autenticação, o que fica registrado como limitação no README. Usa as mesmas regras e ferramentas da CLI (FR-042).

## `POST /chat`

**Requisição**

```json
{"session_id": "uuid-opcional", "mensagem": "Quanto custa o Takamine GD20?"}
```

Sem `session_id`, o servidor cria uma sessão. O cliente não escolhe o id.

**Resposta 200**

```json
{"session_id": "uuid", "resposta": "..."}
```

| Status | Quando |
|--------|--------|
| 200 | Resposta do agente, incluindo o fallback amigável se o LLM falhar |
| 404 | `session_id` desconhecido |
| 422 | Corpo inválido ou `mensagem` vazia |

Mensagens da mesma sessão são processadas uma de cada vez. As sessões ficam em memória e se perdem ao reiniciar. A resposta nunca inclui chamadas de ferramenta.

## `GET /health`

Retorna `{"status": "ok"}` depois que os dados são carregados.
