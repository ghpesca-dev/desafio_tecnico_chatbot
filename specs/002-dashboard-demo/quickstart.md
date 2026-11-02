# Quickstart: Dashboard de Demonstração do Chat

## Preparar

Requer o `.env` configurado, como na [funcionalidade anterior](../001-agente-atendimento/quickstart.md).

```bash
EMPORIO_DATA_REFERENCIA=2026-02-20 uv run --extra api uvicorn emporio.api:app
```

Abra <http://127.0.0.1:8000/>. A data fixada faz os prazos dos pedidos de exemplo funcionarem. Sem ela, vale a data atual.

## Testes sem rede

```bash
uv run pytest -m "not e2e"
```

Esperado: tudo passa, sem gravar em `data/runtime/`.

## Roteiro no navegador

| # | Ação | Esperado |
|---|---|---|
| 1 | Abrir a página | Conversa vazia, perguntas de exemplo, números zerados ou do histórico, aviso de demonstração e data fixada |
| 2 | Enviar "Quanto custa o Takamine GD20?" | Sinal de espera, resposta formatada, consulta `detalhes_produto` e tempo |
| 3 | Enviar "e no PIX?" | Mesmo produto, sem pedir contexto |
| 4 | Enviar "Me passa uma receita de bolo" | Recusa educada, indicação de nenhuma consulta |
| 5 | Pedir nova conversa e enviar "Qual o status do pedido 8?" | Pede e-mail ou telefone, sem dados do pedido |
| 6 | Informar um contato do pedido 8 | Status e rastreio, com contato mascarado na consulta |
| 7 | Alternar entre as conversas e continuar a primeira | Sem misturar contexto |
| 8 | Enviar `<img src=x onerror=alert(1)>` | Aparece como texto, sem alerta |
| 9 | Reiniciar o servidor e recarregar | Conversas e consultas visíveis, somente leitura |
| 10 | Apagar uma conversa e confirmar, depois reiniciar | Ela não volta |
| 11 | Estreitar a janela para largura de celular | Sem rolagem lateral |
| 12 | Desligar a rede e recarregar | A página abre; só o agente mostra contingência |
