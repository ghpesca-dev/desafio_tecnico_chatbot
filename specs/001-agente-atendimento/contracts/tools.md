# Contrato: Ferramentas do LLM

Os schemas JSON são gerados dos modelos Pydantic. As ferramentas retornam JSON, com valores já formatados em reais. Argumento inválido ou erro interno volta como `{"erro": "..."}`, sem interromper o turno. O modelo nunca recebe quantidade em estoque, e-mail, telefone nem ids de cliente.

## `buscar_produtos`

| Argumento | Tipo | Obrigatório | Regra |
|-----------|------|-------------|-------|
| `categoria` | texto | Não | Resolvida contra as categorias carregadas |
| `texto` | texto | Não | Nome ou marca, com busca aproximada |
| `preco_min`, `preco_max` | decimal | Não | Comparados com o preço atual |
| `em_promocao` | booleano | Não | Padrão falso; só promoções ativas |

Retorna apenas produtos disponíveis, por menor preço, até 10.

```json
{
  "total_encontrado": 14,
  "exibidos": 10,
  "categoria_resolvida": "Violões",
  "categoria_sem_itens": false,
  "produtos": [{
    "id": 12, "nome": "...", "categoria": "Violões",
    "preco_atual": "R$ 899,00", "preco_original": "R$ 999,00",
    "desconto_percentual": "10%",
    "preco_exibicao": "R$ 899,00 (de R$ 999,00, 10% de desconto)",
    "promocao": "...", "disponivel": true
  }],
  "promocao_encontrada": null
}
```

`preco_original`, `desconto_percentual` e `promocao` são `null` sem promoção ativa. `promocao_encontrada` traz `nome` e `ativa` se `texto` coincidir com o nome de uma promoção. Se o nome existir só em promoções encerradas, `ativa` é falso e `produtos` não muda por causa dela.

## `detalhes_produto`

| Argumento | Tipo | Obrigatório | Regra |
|-----------|------|-------------|-------|
| `referencia` | texto | Sim | Nome aproximado ou id |

```json
{
  "resultado": "encontrado",
  "produto": {
    "id": 12, "nome": "...", "categoria": "...", "specs": {},
    "situacao": "disponivel", "a_venda": true,
    "preco_tabela": "R$ 999,00", "preco_atual": "R$ 999,00",
    "promocao_ativa": null, "promocao_encerrada": null
  },
  "pagamento": {
    "pix": "R$ 949,05", "pix_nao_acumula": false,
    "parcelas": [{"vezes": 1, "valor": "R$ 999,00"}],
    "max_parcelas": 9
  },
  "alternativas": []
}
```

- `resultado` pode ser `encontrado`, `ambiguo` (com `candidatos`, até 5) ou `nao_encontrado`. Só é `encontrado` se todas as palavras coincidirem, e códigos com número precisam ser exatos. Um único candidato aproximado continua `ambiguo`, para o cliente confirmar.
- `situacao` segue o [modelo de dados](../data-model.md). `a_venda` só é verdadeiro com `disponivel`. `pagamento` é `null` com `em_breve`, `fora_de_catalogo` e `sem_informacao`.
- `alternativas`: até 3 produtos disponíveis da mesma categoria, com preço mais próximo.
- Com promoção ativa, `pix` é o preço promocional e `pix_nao_acumula` é verdadeiro.

Sem resultado, `buscar_produtos` e `detalhes_produto` devolvem `orientacao`, com o texto a seguir e o contato da loja.

## `consultar_pedido`

| Argumento | Tipo | Obrigatório | Regra |
|-----------|------|-------------|-------|
| `numero_pedido` | inteiro | Sim | |
| `contato` | texto | Não | E-mail ou telefone; dispensado se o pedido já foi confirmado na sessão |

Sempre fornecido com o `SessionState`, que o modelo não vê.

| Resultado | Quando | Conta como falha |
|-----------|--------|------------------|
| `ok` | Confirmado | Não |
| `precisa_confirmacao` | Sem contato, ou contato que o cliente não escreveu depois da última confirmação | Não |
| `nao_confirmado` | Pedido inexistente ou dado incorreto; texto idêntico nos dois casos | Sim |
| `bloqueado` | Três falhas na sessão | Não |

```json
{
  "resultado": "ok",
  "pedido": {
    "numero": 8, "primeiro_nome": "...", "status": "entregue",
    "data": "2026-10-20", "total": "R$ 1.299,00", "pagamento": "...",
    "rastreio": null, "previsao_entrega": "2026-10-27", "motivo_cancelamento": null,
    "itens": [{"nome": "...", "quantidade": 1}],
    "prazos": {
      "arrependimento": {"situacao": "no_prazo", "ate": "2026-11-03", "base": "previsao_entrega"},
      "troca_preferencia": {"situacao": "no_prazo", "ate": "2026-11-03", "base": "previsao_entrega"},
      "defeito": {"situacao": "no_prazo", "ate": "2026-11-19", "base": "data_compra"},
      "garantia_legal": {"situacao": "no_prazo", "ate": "2027-01-25", "base": "previsao_entrega"}
    }
  }
}
```

Fora de `ok`, a saída traz `orientacao`, com o texto que o agente deve seguir, e nenhum dado do pedido. `motivo_cancelamento` só vem preenchido em pedido cancelado, porque `notes` pode guardar anotações internas.

`situacao` do prazo: `no_prazo`, `encerrado`, `indeterminado`, `nao_iniciado` ou `nao_se_aplica`. Com `indeterminado`, o agente não conclui e encaminha para a equipe. Os itens não trazem valor, porque a fonte não registra o preço pago por item.

## `consultar_politica`

| Argumento | Tipo | Obrigatório | Regra |
|-----------|------|-------------|-------|
| `topico` | enum | Sim | `loja`, `horario`, `pagamento`, `trocas_devolucoes`, `frete`, `promocoes`, `atendimento`, `garantia`, `privacidade` |

Retorna `{"topico": "...", "texto": "..."}`.

## `registrar_reclamacao`

| Argumento | Tipo | Obrigatório | Regra |
|-----------|------|-------------|-------|
| `resumo` | texto | Sim | Não vazio |
| `contato` | texto | Sim | Não vazio |
| `nome`, `numero_pedido` | texto, inteiro | Não | |

Retorna `{"registrada": true, "protocolo": "..."}`. Em falha, retorna `{"registrada": false}`, e o agente passa o telefone, sem prometer retorno.
