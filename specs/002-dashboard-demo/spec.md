# Feature Specification: Dashboard de Demonstração do Chat

**Feature Branch**: `002-dashboard-demo` (ainda não criada: o trabalho segue em `001-agente-atendimento` até a decisão de criar a branch)

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "quero criar um dashboard simples para demonstração do chat, com um historico de conversa"

## User Scenarios & Testing *(mandatory)*

O público desta funcionalidade é quem apresenta ou avalia o projeto, não o cliente da loja. O agente continua o mesmo: as regras de preço, estoque, pedidos e identidade não mudam, e o dashboard só mostra o que ele faz.

### User Story 1 - Conversar com o agente pelo navegador (Priority: P1)

Como pessoa que apresenta o projeto, quero abrir uma página no navegador e conversar com o agente, para demonstrar o atendimento sem usar o terminal.

**Why this priority**: Sem isso não há demonstração. Sozinha, esta história já substitui o terminal numa apresentação.

**Independent Test**: Abrir a página, enviar perguntas da loja e conferir que as respostas são iguais em conteúdo às da interface de texto.

**Acceptance Scenarios**:

1. **Dado** a aplicação em execução, **Quando** a pessoa abre o dashboard, **Então** vê uma conversa vazia, pronta para receber a primeira mensagem.
2. **Dado** uma conversa aberta, **Quando** a pessoa envia "Quanto custa o Takamine GD20?", **Então** a mensagem aparece na conversa, há um sinal de que o agente está respondendo e a resposta aparece em seguida.
3. **Dado** uma conversa em andamento, **Quando** a pessoa envia "e no PIX?", **Então** o agente responde sobre o mesmo produto, sem pedir o contexto de novo.
4. **Dado** uma resposta com listas ou destaques, **Quando** ela aparece, **Então** é exibida formatada e fácil de ler, sem marcas de formatação à vista.
5. **Dado** que o agente está respondendo, **Quando** a pessoa tenta enviar outra mensagem na mesma conversa, **Então** o envio fica impedido até a resposta chegar.

---

### User Story 2 - Consultar o histórico de conversas (Priority: P1)

Como pessoa que apresenta o projeto, quero ver a lista das conversas e abrir qualquer uma delas, para mostrar atendimentos anteriores e retomar uma demonstração.

**Why this priority**: É o pedido explícito da funcionalidade e permite mostrar casos já prontos, sem gastar novas consultas ao modelo.

**Independent Test**: Criar duas conversas, alternar entre elas, reiniciar a aplicação e confirmar que as duas continuam na lista com todas as mensagens.

**Acceptance Scenarios**:

1. **Dado** conversas já realizadas, **Quando** a pessoa abre o dashboard, **Então** vê a lista delas, da mais recente para a mais antiga, cada uma com título, data e hora da última mensagem.
2. **Dado** a lista de conversas, **Quando** a pessoa escolhe uma, **Então** vê todas as mensagens dela, na ordem em que aconteceram.
3. **Dado** uma conversa aberta, **Quando** a pessoa pede uma nova conversa, **Então** começa uma conversa vazia, sem contexto da anterior, e a anterior continua na lista.
4. **Dado** duas conversas, **Quando** a pessoa alterna entre elas e continua uma delas, **Então** o agente mantém o contexto daquela conversa, sem misturar com a outra.
5. **Dado** que a aplicação foi reiniciada, **Quando** a pessoa abre uma conversa anterior, **Então** as mensagens continuam visíveis, marcadas como somente leitura, e há como começar uma nova.
6. **Dado** o histórico, **Quando** a pessoa apaga uma conversa e confirma, **Então** ela some da lista e não volta depois de reiniciar a aplicação.

---

### User Story 3 - Ver como o agente chegou à resposta (Priority: P2)

Como pessoa que avalia o projeto, quero ver quais consultas o agente fez em cada resposta, para confirmar que preço, estoque e políticas vêm das fontes da loja e não da imaginação do modelo.

**Why this priority**: É o principal diferencial técnico do projeto, mas a conversa funciona sem isso.

**Independent Test**: Enviar uma pergunta de preço, uma de política e uma fora do tema, e conferir as consultas mostradas em cada resposta.

**Acceptance Scenarios**:

1. **Dado** uma resposta que consultou a loja, **Quando** a pessoa olha essa resposta, **Então** vê quais consultas foram feitas, com os parâmetros usados, e quanto tempo a resposta levou.
2. **Dado** uma resposta sem consulta, como uma recusa fora do tema, **Quando** a pessoa olha essa resposta, **Então** vê que nenhuma consulta foi feita.
3. **Dado** uma consulta de pedido, **Quando** seus parâmetros são exibidos, **Então** o e-mail ou telefone aparece mascarado.
4. **Dado** uma conversa reaberta do histórico, **Quando** a pessoa olha as respostas antigas, **Então** vê as mesmas consultas e tempos registrados na hora.

---

### User Story 4 - Ver os números da demonstração (Priority: P3)

Como pessoa que apresenta o projeto, quero ver alguns números no topo do dashboard, para mostrar de relance como o agente está sendo usado.

**Why this priority**: Dá cara de painel à demonstração, mas não muda o que pode ser mostrado.

**Independent Test**: Conferir os números contra uma contagem manual de um histórico conhecido.

**Acceptance Scenarios**:

1. **Dado** o histórico, **Quando** a pessoa abre o dashboard, **Então** vê o total de conversas, o total de mensagens de clientes, o tempo médio de resposta e as consultas mais usadas.
2. **Dado** uma nova resposta, **Quando** ela termina, **Então** os números são atualizados sem recarregar a página.
3. **Dado** um histórico vazio, **Quando** a pessoa abre o dashboard, **Então** os números aparecem zerados, sem erro.

---

### User Story 5 - Preparar a demonstração em poucos cliques (Priority: P3)

Como pessoa que apresenta o projeto, quero perguntas de exemplo prontas, para mostrar os principais casos sem digitar nem esquecer nenhum.

**Why this priority**: Facilita a apresentação, mas tudo pode ser digitado à mão.

**Independent Test**: Usar cada pergunta de exemplo numa conversa nova e confirmar que o agente responde.

**Acceptance Scenarios**:

1. **Dado** uma conversa vazia, **Quando** a pessoa olha a tela, **Então** vê perguntas de exemplo de produto, promoção, pedido, política e fora de escopo.
2. **Dado** uma pergunta de exemplo, **Quando** a pessoa a escolhe, **Então** ela é enviada como se tivesse sido digitada.

---

### Edge Cases

- **Modelo indisponível ou lento**: a conversa mostra a mesma mensagem de contingência da interface de texto, com o telefone da loja, e permite tentar de novo. A mensagem que falhou continua visível.
- **Mensagem vazia ou só com espaços**: não é enviada.
- **Mensagem muito longa**: segue o mesmo comportamento das outras interfaces, e a tela continua legível.
- **Conteúdo com marcação ou código digitado pelo usuário**: é exibido como texto, sem ser executado, tanto na conversa quanto no título do histórico.
- **Arquivo de histórico ausente**: a aplicação começa com a lista vazia.
- **Arquivo de histórico danificado**: as conversas legíveis aparecem, as demais são ignoradas com aviso no registro, e a aplicação não para.
- **Duas abas na mesma conversa**: a segunda mensagem espera a primeira terminar, e a conversa não se corrompe. Ao recarregar, a aba mostra o estado salvo.
- **Sessão bloqueada por falhas de confirmação de identidade**: o dashboard mostra a resposta do agente normalmente. Ao começar uma nova conversa, vale a mesma regra das outras interfaces.
- **Reinício com conversa em andamento**: a resposta em curso se perde, a página informa a falha e a conversa fica somente leitura.
- **Conversa longa**: o histórico mostra todas as mensagens, mesmo quando o modelo recebe só a janela recente.
- **Pedidos com prazos antigos**: com a data de referência fixada para a demonstração, os prazos são calculados como na interface de texto.
- **Tela estreita**: o dashboard continua utilizável no celular, sem rolagem lateral.

## Requirements *(mandatory)*

### Functional Requirements

**Conversa**

- **FR-001**: O sistema DEVE oferecer uma página web em que a pessoa troca mensagens com o agente.
- **FR-002**: As respostas DEVEM vir do mesmo agente das outras interfaces, com as mesmas regras e fontes. O dashboard NÃO DEVE calcular nem alterar preços, prazos ou decisões sobre pedidos.
- **FR-003**: O sistema DEVE manter o contexto de cada conversa e permitir perguntas de seguimento.
- **FR-004**: O sistema DEVE mostrar que uma resposta está em andamento e impedir um novo envio na mesma conversa até ela terminar.
- **FR-005**: O sistema DEVE exibir respostas formatadas e mostrar todo conteúdo de usuário ou do agente sem executar marcações.
- **FR-006**: Em falha do modelo, o sistema DEVE mostrar a mensagem de contingência com o contato da loja e manter a conversa utilizável.
- **FR-007**: O sistema DEVE permitir fixar a data de referência ao iniciar, como na interface de texto, e mostrar essa data na tela quando ela estiver fixada.

**Histórico**

- **FR-008**: O sistema DEVE registrar cada conversa com suas mensagens, horários, consultas feitas e tempos de resposta.
- **FR-009**: O histórico DEVE sobreviver ao reinício da aplicação.
- **FR-010**: O sistema DEVE listar as conversas da mais recente para a mais antiga, com título, data e hora da última mensagem.
- **FR-011**: O título de cada conversa DEVE vir da primeira mensagem do cliente, encurtado para caber na lista.
- **FR-012**: O sistema DEVE permitir abrir qualquer conversa e ver todas as suas mensagens, mesmo as que já saíram da janela enviada ao modelo.
- **FR-013**: O sistema DEVE permitir começar uma nova conversa a qualquer momento, sem contexto da anterior.
- **FR-014**: Conversas abertas antes do último reinício DEVEM ficar somente leitura.
- **FR-015**: Confirmações de identidade NÃO DEVEM ser restauradas do histórico. Uma confirmação vale só para a conversa em que ocorreu, enquanto a aplicação estiver em execução.
- **FR-016**: O sistema DEVE permitir apagar uma conversa, depois de confirmação da pessoa.
- **FR-017**: O sistema DEVE tolerar histórico ausente ou parcialmente danificado sem deixar de iniciar.

**Transparência**

- **FR-018**: Para cada resposta, o sistema DEVE mostrar as consultas feitas, com seus parâmetros, e o tempo de resposta.
- **FR-019**: O sistema DEVE indicar quando uma resposta não usou consultas.
- **FR-020**: E-mail e telefone DEVEM aparecer mascarados nos parâmetros de consulta, na tela e no que for registrado para esse fim.
- **FR-021**: Os dados internos da loja que o agente recebe nas consultas NÃO DEVEM ser mostrados integralmente. O dashboard mostra o que foi consultado, não o resultado bruto.

**Números e exemplos**

- **FR-022**: O sistema DEVE mostrar o total de conversas, o total de mensagens de clientes, o tempo médio de resposta e as consultas mais usadas, calculados a partir do histórico.
- **FR-023**: Os números DEVEM ser atualizados ao fim de cada resposta, sem recarregar a página.
- **FR-024**: O sistema DEVE oferecer perguntas de exemplo cobrindo produto, promoção, pedido, política e fora de escopo.

**Uso local**

- **FR-025**: O dashboard DEVE ficar disponível só no próprio computador por padrão, e a página DEVE informar que é uma demonstração sem autenticação.
- **FR-026**: O histórico DEVE ficar fora do repositório, junto dos demais dados gerados em execução.
- **FR-027**: As interfaces já existentes DEVEM continuar funcionando como antes.
- **FR-028**: O dashboard DEVE funcionar sem acesso à internet para carregar a própria página. Só as respostas do modelo dependem de rede.

### Key Entities

- **Conversa**: identificador, título, início, última mensagem, situação (ativa ou somente leitura) e mensagens.
- **Mensagem**: autor (cliente ou agente), texto e horário. A do agente também tem tempo de resposta e consultas.
- **Consulta**: nome, parâmetros com contato mascarado e duração.
- **Indicadores**: valores calculados a partir do histórico, sem registro próprio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma pessoa que nunca viu o projeto envia a primeira mensagem em até 30 segundos depois de abrir o dashboard, sem instruções.
- **SC-002**: Em 100% de um conjunto de perguntas de teste, o conteúdo factual (preços, estoque, prazos, status) é igual ao da interface de texto.
- **SC-003**: 100% das conversas e mensagens continuam disponíveis depois de reiniciar a aplicação.
- **SC-004**: Abrir uma conversa do histórico com até 100 mensagens leva menos de 1 segundo, e a página fica pronta em menos de 2 segundos com até 200 conversas salvas.
- **SC-005**: O dashboard acrescenta menos de 1 segundo ao tempo de resposta do agente.
- **SC-006**: Em 100% das respostas de teste, a pessoa consegue dizer quais consultas foram feitas, sem abrir registros técnicos.
- **SC-007**: Nenhum e-mail ou telefone aparece sem máscara nos parâmetros de consulta, e nenhum dado de pedido fica acessível numa conversa retomada sem nova confirmação.
- **SC-008**: Uma demonstração completa, com um caso de produto, um de pedido e um de política, leva menos de 5 minutos.

## Assumptions

- "Dashboard" significa uma página de demonstração com chat, histórico, transparência das consultas e poucos números. Não é um painel gerencial para a loja.
- "Histórico" significa a lista de conversas salvas, não apenas o contexto da conversa atual, que já existe.
- O uso é local e por uma pessoa de cada vez, sem contas de usuário. Publicar o dashboard na internet está fora de escopo.
- O histórico fica no computador em que a aplicação roda e pode conter dados pessoais digitados nas conversas. Isso é aceitável numa demonstração com dados fictícios.
- Conversas anteriores ao reinício ficam somente leitura para não restaurar confirmações de identidade.
- Fora de escopo: edição de mensagens, busca e exportação do histórico, respostas em tempo real palavra por palavra, gráficos históricos, temas personalizados e atendimento humano pelo painel.
- O histórico não tem limite automático de tamanho nem de retenção. Quem usa pode apagar conversas.
- Depende do agente, da API opcional e dos dados já entregues na funcionalidade `001-agente-atendimento`, além de uma chave válida do provedor de modelos.
- O modelo usado é o configurado no ambiente. A qualidade das respostas depende dele, e os resultados de validação do projeto valem para o modelo padrão.
