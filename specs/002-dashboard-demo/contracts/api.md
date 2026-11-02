# Contrato HTTP do Dashboard

Sem autenticação. Uso em `127.0.0.1`.

## `GET /`

Devolve a página `dashboard.html`.

## `POST /chat`

Contrato inalterado. Corpo `{"session_id": "...", "mensagem": "..."}`, com `session_id` omitido na primeira mensagem. Devolve `{"session_id": "...", "resposta": "..."}`, sem consultas.

| Situação | Status |
|---|---|
| Mensagem vazia | 422 |
| Sessão que não está em memória, inclusive depois de reinício | 404 |
| Sessão apagada enquanto a mensagem esperava a vez | 404 |

Efeito novo: grava a troca no histórico. Uma falha de gravação vai para o log e não impede a resposta.

## `GET /conversas`

```json
{
  "data_referencia": "2026-02-20",
  "conversas": [
    {
      "id": "b011a898-...",
      "titulo": "Quanto custa o Takamine GD20?",
      "atualizada_em": "2026-11-01T10:30:00-04:00",
      "somente_leitura": false
    }
  ],
  "indicadores": {
    "conversas": 1,
    "mensagens_cliente": 2,
    "tempo_medio_ms": 3200,
    "consultas_mais_usadas": [{"nome": "detalhes_produto", "total": 2}]
  }
}
```

`data_referencia` é `null` sem data fixada. A lista vem da mais recente para a mais antiga, e arquivos ilegíveis são ignorados com aviso no log.

## `GET /conversas/{id}`

Devolve a Conversa completa do [modelo de dados](../data-model.md), com `somente_leitura`. Responde 404 para `id` inválido ou inexistente.

## `DELETE /conversas/{id}`

Apaga o arquivo e a sessão em memória, esperando a resposta em andamento. Responde 204, ou 404 para `id` inválido ou inexistente. A confirmação fica na página.
