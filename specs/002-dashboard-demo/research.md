# Research: Dashboard de Demonstração do Chat

Critério geral, pedido pelo usuário: a opção mais fácil e simples que atenda à spec.

## 1. Interface

- **Decisão**: um único `dashboard.html`, com CSS e JavaScript puro no próprio arquivo, servido por `GET /`.
- **Motivo**: não exige build nem dependências, e funciona sem internet (FR-028).
- **Alternativas**: React ou Vue exigiriam build ou CDN. Streamlit e Gradio trariam dependências pesadas e layout menos controlável, além de um segundo servidor. Jinja não acrescenta nada, porque os dados vêm da API.

## 2. Armazenamento do histórico

- **Decisão**: um arquivo JSON por conversa, em `data/runtime/conversas/<id>.json`, regravado a cada troca com arquivo temporário e `os.replace`.
- **Motivo**: apagar é remover o arquivo, um arquivo danificado não afeta os outros (FR-017) e a gravação é atômica.
- **Alternativas**: JSONL único, como nas reclamações, exigiria reescrever tudo para apagar, e uma linha danificada no meio de um registro é pior de tratar. SQLite resolveria, mas pede esquema e migração sem ganho nesta escala.

## 3. Como a página recebe consultas e tempos

- **Decisão**: `POST /chat` não muda. A API grava o histórico e a página, ao receber a resposta, chama `GET /conversas/{id}`.
- **Motivo**: mantém o contrato e o teste que garante que `/chat` não expõe ferramentas (FR-027). Uma fonte só de verdade: o que aparece ao vivo é o que aparece depois do reinício (cenário 4 da US3).
- **Alternativas**: acrescentar campos a `/chat` quebraria esse teste. Streaming está fora de escopo.

## 4. Captura das consultas no agente

- **Decisão**: campo `consultas_turno` em `SessionState`, limpo no início de `responder` e preenchido em `_executar_chamadas`.
- **Motivo**: `responder` continua devolvendo `str`, então a CLI e os testes não mudam. As durações só existem nesse ponto.
- **Alternativas**: ler as chamadas em `sessao.mensagens` perde as durações e falha com rollback. Devolver um objeto obrigaria a mudar todos os chamadores.

## 5. Máscara de contato

- **Decisão**: `mascarar_argumentos` passa a trocar também e-mails e sequências de 8 ou mais dígitos dentro de qualquer texto, além do campo `contato`.
- **Motivo**: `registrar_reclamacao` recebe um resumo livre, que pode trazer o contato do cliente. Sem isso, o FR-020 e o SC-007 não seriam garantidos.
- **Alternativas**: esconder os parâmetros dessa ferramenta perderia transparência. Um campo a mais na lista de mascarados não cobre texto livre.

## 6. Somente leitura após reinício

- **Decisão**: uma conversa é somente leitura quando existe no disco e não existe no dicionário de sessões em memória. `SessionState` nunca é restaurado do histórico.
- **Motivo**: não há estado novo para manter, e as confirmações de identidade não voltam (FR-014 e FR-015).
- **Alternativas**: reconstruir a sessão a partir do histórico exigiria decidir quais confirmações valem, e é justamente o risco a evitar.

## 7. Data de referência

- **Decisão**: usar `EMPORIO_DATA_REFERENCIA`, que `carregar_config` já lê, e expor o valor em `GET /conversas`.
- **Motivo**: nada a construir. `uvicorn` não recebe `--data`, mas a variável resolve (FR-007).
- **Observação**: os horários do histórico usam o relógio real, não a data fixada. Caso contrário, conversas de dias diferentes ficariam fora de ordem.

## 8. Formatação das respostas

- **Decisão**: um renderizador de poucas linhas para parágrafos, listas e negrito, que monta elementos com `textContent` e nunca usa `innerHTML`.
- **Motivo**: seguro por construção contra marcação vinda do usuário ou do modelo (FR-005), sem biblioteca.
- **Alternativas**: `marked` com `DOMPurify` acrescentaria dois arquivos para copiar ou uma CDN. O limite é que tabelas e links em Markdown aparecem como texto simples.

## 9. Testes

- **Decisão**: rotas e histórico testados com pytest sem rede. A página é conferida à mão no navegador, mais uma verificação automática de que não usa `innerHTML` nem recursos externos.
- **Motivo**: um framework de teste de navegador seria uma dependência grande para um único arquivo. Não há navegador instalado no WSL deste ambiente.

## Pontos em aberto

Nenhum.
