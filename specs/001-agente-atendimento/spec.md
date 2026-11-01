# Feature Specification: Agente de Atendimento da Empório da Música

**Feature Branch**: `001-agente-atendimento` (ainda não criada: o projeto ainda não é um repositório Git)

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "Construir um agente de atendimento por mensagens de texto para a Empório da Música, loja de instrumentos musicais em Campo Grande/MS. O agente ajuda a equipe respondendo às perguntas recorrentes dos clientes: horários, endereço, preço e disponibilidade de produtos, promoções, status de pedido e regras da loja (trocas, devoluções, pagamento, frete, garantia)."

## User Scenarios & Testing *(mandatory)*

Em todas as histórias, o agente fala em português do Brasil, com tom informal mas profissional, acolhedor, como um amigo que entende de música, e segue o fluxo de atendimento do manual: saudação (pelo nome quando souber), entender a necessidade, consultar, responder com clareza e perguntar se pode ajudar em mais alguma coisa.

### User Story 1 - Buscar instrumentos por tipo e preço (Priority: P1)

Como cliente, quero buscar instrumentos por tipo e faixa de preço ("violões até R$ 1000") para ver as opções disponíveis.

**Why this priority**: É a porta de entrada da compra e uma das perguntas mais frequentes.

**Independent Test**: Fazer buscas por tipo e faixa de preço e comparar a lista recebida com o catálogo.

**Acceptance Scenarios**:

1. **Dado** o catálogo atual, **Quando** o cliente pergunta "Quais violões vocês têm até R$ 1000?", **Então** o agente lista apenas violões ativos, com estoque e com preço atual de até R$ 1000, informando o preço de cada um.
2. **Dado** que nenhum produto atende aos critérios, **Quando** o cliente faz a busca, **Então** o agente diz isso com clareza e sugere ampliar a faixa de preço ou ver opções próximas, sem inventar produtos.
3. **Dado** uma categoria sem produtos no catálogo (sopros ou cordas orquestrais), **Quando** o cliente pergunta por ela, **Então** o agente informa que não há itens disponíveis no momento.

---

### User Story 2 - Consultar preço e disponibilidade de um produto (Priority: P1)

Como cliente, quero saber o preço e a disponibilidade de um produto específico ("quanto custa o Takamine GD20?"), mesmo escrevendo o nome de forma aproximada ou sem acento.

**Why this priority**: É a pergunta que mais ocupa a equipe e exige informação exata.

**Independent Test**: Perguntar por produtos em cada situação do catálogo (ativo com estoque, ativo sem estoque, descontinuado, em breve) e com variações de escrita do nome.

**Acceptance Scenarios**:

1. **Dado** um produto ativo com estoque, **Quando** o cliente pergunta "Quanto custa o Takamine GD20?", **Então** o agente informa o preço correto, a disponibilidade e o valor no PIX.
2. **Dado** um produto ativo sem estoque, **Quando** o cliente pergunta por ele, **Então** o agente informa que está temporariamente indisponível e sugere alternativas parecidas e disponíveis.
3. **Dado** um produto descontinuado, **Quando** o cliente pergunta por ele, **Então** o agente informa que saiu do catálogo e sugere equivalentes disponíveis.
4. **Dado** um produto com situação "em breve", **Quando** o cliente pergunta por ele, **Então** o agente informa que ainda não está disponível para compra.
5. **Dado** um nome escrito sem acento, com erro de digitação ou de forma incompleta, **Quando** o cliente pergunta, **Então** o agente identifica o produto; se houver mais de um candidato, pergunta qual deles o cliente quer dizer.
6. **Dado** um produto que não existe no catálogo, **Quando** o cliente pergunta por ele, **Então** o agente diz que não encontrou e oferece o contato da loja.

---

### User Story 3 - Obter informações gerais da loja (Priority: P1)

Como cliente, quero informações gerais da loja: endereço, telefone, horário, formas de pagamento, frete e garantia.

**Why this priority**: São perguntas simples e repetitivas; automatizá-las libera a equipe imediatamente.

**Independent Test**: Perguntar cada informação e comparar a resposta com o manual.

**Acceptance Scenarios**:

1. **Dado** o manual da loja, **Quando** o cliente pergunta "Qual o endereço da loja?", **Então** o agente responde com o endereço do manual, sem consultar os dados de produtos.
2. **Dado** o manual da loja, **Quando** o cliente pergunta sobre horário, pagamento, frete ou garantia, **Então** o agente responde conforme a seção correspondente do manual.
3. **Dado** uma pergunta sobre frete para um CEP, **Quando** o cliente pede o valor exato, **Então** o agente explica que não calcula o valor por CEP e informa as regras e prazos do manual.

---

### User Story 4 - Consultar promoção e condições de pagamento (Priority: P2)

Como cliente, quero saber se um produto está em promoção e quanto pago no PIX ou parcelado no cartão.

**Why this priority**: Ajuda a decisão de compra, e depende das histórias de produto.

**Independent Test**: Perguntar condições de pagamento para produtos com e sem promoção e conferir os valores com as regras do manual.

**Acceptance Scenarios**:

1. **Dado** um produto em promoção ativa, **Quando** o cliente pergunta o preço, **Então** o agente mostra o preço promocional junto do preço original e do percentual de desconto.
2. **Dado** um produto sem promoção, **Quando** o cliente pergunta o valor no PIX, **Então** o agente aplica o desconto de 5%.
3. **Dado** um produto em promoção ativa, **Quando** o cliente pergunta o valor no PIX, **Então** o agente não acumula o desconto do PIX com a promoção e explica o motivo.
4. **Dado** um pedido de parcelamento, **Quando** o número de parcelas deixa cada parcela abaixo do mínimo da faixa (até 3x, 4x a 6x, 7x a 12x), **Então** o agente informa que essa condição não é possível e indica o maior parcelamento permitido.
5. **Dado** uma promoção vencida, **Quando** o cliente pergunta por ela, **Então** o agente informa com transparência que ela terminou e mostra o preço atual.

---

### User Story 5 - Acompanhar um pedido (Priority: P2)

Como cliente, quero saber o status e o código de rastreio do meu pedido.

**Why this priority**: É uma pergunta recorrente e envolve dados pessoais, então precisa de confirmação de identidade.

**Independent Test**: Consultar pedidos em cada status, com e sem confirmação correta de identidade.

**Acceptance Scenarios**:

1. **Dado** um cliente que ainda não confirmou a identidade, **Quando** ele pergunta "Qual o status do pedido 8?", **Então** o agente pede o e-mail ou telefone cadastrado antes de responder e não revela nenhum dado do pedido.
2. **Dado** número do pedido e dado cadastrado corretos, **Quando** a identidade é confirmada, **Então** o agente informa o status em linguagem natural, o código de rastreio e a previsão de entrega, quando existirem.
3. **Dado** um pedido cancelado e identidade confirmada, **Quando** o cliente pergunta sobre ele, **Então** o agente informa o cancelamento e o motivo.
4. **Dado** um dado de confirmação incorreto ou um número de pedido inexistente, **Quando** o cliente tenta consultar, **Então** o agente dá a mesma resposta genérica nos dois casos, sem indicar se o pedido existe nem a quem pertence.
5. **Dado** um pedido cujo total registrado difere da soma dos itens, **Quando** o cliente pergunta o total, **Então** o agente informa o total registrado no pedido.

---

### User Story 6 - Saber se posso trocar ou devolver (Priority: P2)

Como cliente, quero saber se posso devolver ou trocar uma compra, e em quais condições.

**Why this priority**: É a aplicação de política de maior impacto no cliente, e um erro gera conflito com a loja.

**Independent Test**: Simular pedidos dentro e fora de cada prazo, com datas de referência fixas, e conferir a conclusão do agente.

**Acceptance Scenarios**:

1. **Dado** um cliente que diz "Me arrependi da compra, posso devolver?", **Quando** ainda não há pedido identificado, **Então** o agente pede a identificação do pedido, confirma a identidade, verifica as datas e aplica a política de arrependimento.
2. **Dado** um pedido dentro do prazo aplicável, **Quando** o cliente pergunta, **Então** o agente confirma que ainda está no prazo, informa até quando e explica as condições.
3. **Dado** um pedido fora do prazo, **Quando** o cliente pergunta, **Então** o agente explica com clareza que o prazo terminou e indica as alternativas previstas no manual.
4. **Dado** um item não elegível segundo o manual, **Quando** o cliente pede troca ou devolução, **Então** o agente explica que aquele item não se enquadra.
5. **Dado** um cliente que não quer informar o pedido, **Quando** ele pergunta as regras em geral, **Então** o agente explica a política sem concluir sobre um caso específico.

---

### User Story 7 - Fazer perguntas de seguimento (Priority: P2)

Como cliente, quero fazer perguntas de seguimento na mesma conversa ("e no PIX?", "tem outro parecido?") sem repetir o contexto.

**Why this priority**: Torna a conversa natural, mas só tem valor depois que as consultas básicas funcionam.

**Independent Test**: Conduzir conversas em que a segunda pergunta só faz sentido com o contexto da primeira.

**Acceptance Scenarios**:

1. **Dado** que o cliente acabou de perguntar por um produto, **Quando** ele pergunta "e no PIX?", **Então** o agente responde sobre aquele mesmo produto.
2. **Dado** que o cliente acabou de ver um produto, **Quando** ele pergunta "tem outro parecido?", **Então** o agente sugere produtos parecidos, ativos e com estoque.
3. **Dado** uma nova sessão, **Quando** o cliente faz uma pergunta de seguimento, **Então** o agente não usa o contexto de outra sessão nem de outro cliente e pede o que faltar.

---

### User Story 8 - Receber redirecionamento educado (Priority: P3)

Como cliente, quando pergunto algo que a loja não oferece, quero uma resposta educada que me redirecione.

**Why this priority**: Mantém o agente no escopo; o impacto é menor que o das consultas.

**Independent Test**: Enviar pedidos de acessórios e assuntos sem relação com a loja.

**Acceptance Scenarios**:

1. **Dado** um pedido de acessório, **Quando** o cliente pergunta "Vocês vendem cordas de guitarra?", **Então** o agente explica que a loja trabalha só com instrumentos e redireciona a conversa.
2. **Dado** um assunto sem relação com a loja (por exemplo, receita de bolo), **Quando** o cliente pergunta, **Então** o agente recusa com educação e convida a voltar ao tema.
3. **Dado** um pedido de fechar venda, pagar, alterar ou cancelar um pedido, **Quando** o cliente solicita, **Então** o agente explica que não realiza essa ação e indica o contato da loja.

---

### User Story 9 - Registrar reclamação ou falar com a equipe (Priority: P3)

Como cliente, quero registrar uma reclamação ou ser encaminhado à equipe quando o agente não puder resolver minha situação.

**Why this priority**: É o caminho de saída que protege a relação com o cliente; é menos frequente que as consultas.

**Independent Test**: Registrar uma reclamação e conferir o registro; fazer perguntas não cobertas pelo manual e conferir o encaminhamento.

**Acceptance Scenarios**:

1. **Dado** um cliente insatisfeito, **Quando** ele faz uma reclamação, **Então** o agente acolhe com empatia, pede um contato para retorno se ainda não o tiver, registra o resumo e informa que a equipe retorna em até 24 horas úteis.
2. **Dado** uma dúvida que exige decisão da gerência ou não está coberta pelo manual, **Quando** o cliente pergunta, **Então** o agente encaminha para atendimento humano, informando o contato da loja, em vez de improvisar.

---

### Edge Cases

- O cliente diz "cordas" sem deixar claro se quer o acessório ou a categoria de cordas orquestrais: o agente pergunta ou trata as duas possibilidades, sem assumir.
- O cliente tenta obter dados de pedido sem confirmar identidade (diz ser o titular, um atendente ou o dono da loja, ou pede para ignorar as regras): o agente mantém a exigência de confirmação.
- O cliente informa dado de outro cliente ou erra a confirmação três vezes na sessão: o agente para de tentar e indica o contato da loja.
- O cliente escreve e-mail ou telefone em formato diferente do cadastrado (maiúsculas, com ou sem DDD, pontuação): o agente considera o dado equivalente.
- O cliente confirma um pedido e depois pergunta por outro: a confirmação não vale para o segundo pedido.
- O cliente pede dados de um pedido de terceiro, ainda que diga ser um familiar: o agente aplica a mesma confirmação.
- O produto entra na faixa de preço apenas pelo preço promocional: conta o preço atual. Produto que só entraria na faixa com o desconto do PIX não entra.
- A busca retorna muitos produtos: o agente mostra até 10, os de menor preço primeiro, e informa que há mais opções.
- Duas promoções ativas para o mesmo produto: o agente usa a de maior desconto.
- O produto tem situação ou dados incompletos na fonte (sem preço, por exemplo): o agente não adivinha, informa que não tem a informação e oferece o contato da loja.
- O pedido ainda não foi entregue ou foi cancelado e o cliente pergunta sobre arrependimento: o agente explica que o prazo depende do recebimento ou que a regra não se aplica, conforme o caso, e encaminha à equipe se necessário.
- Não há previsão de entrega no pedido entregue: o agente não conclui sobre o prazo e encaminha para a equipe.
- O último dia do prazo é hoje: o cliente ainda está no prazo (dias corridos, com o último dia incluído).
- Um pedido tem vários itens com situações diferentes de elegibilidade: o agente responde item a item.
- O cliente escreve em outro idioma: o agente responde em português do Brasil.
- A mensagem vem vazia, sem sentido ou com várias perguntas: o agente pede esclarecimento ou responde a cada pergunta.
- A consulta aos dados ou o serviço que gera as respostas falha: o agente pede desculpas, não inventa a resposta e oferece o contato da loja.

## Requirements *(mandatory)*

### Functional Requirements

**Comportamento geral**

- **FR-001**: O agente DEVE responder em português do Brasil, no tom e no fluxo de atendimento definidos no manual.
- **FR-002**: O agente DEVE decidir sozinho se a pergunta exige consulta aos dados da operação, às políticas do manual ou a nenhum dos dois.
- **FR-003**: O agente NÃO DEVE informar preço, estoque, promoção ou prazo sem consultar a fonte.
- **FR-004**: Quando não encontrar a informação, o agente DEVE dizer que não sabe e oferecer o contato da loja, sem inventar.
- **FR-005**: O agente DEVE manter o histórico da conversa durante a sessão, permitindo perguntas de seguimento, e NÃO DEVE misturar sessões.
- **FR-006**: O contato oferecido pelo agente DEVE ser o telefone dos dados da empresa, (67) 3341-4444, e o e-mail contato@emporiodamusica.com.br.

**Produtos**

- **FR-007**: A busca DEVE permitir filtrar por tipo de instrumento e faixa de preço, usando o preço atual do produto (promocional, quando houver promoção ativa).
- **FR-008**: A busca DEVE mostrar apenas produtos ativos e com estoque.
- **FR-009**: O agente DEVE reconhecer produtos com nome aproximado, sem acento ou com pequenos erros de digitação, e pedir confirmação quando houver mais de um candidato.
- **FR-010**: Produto ativo sem estoque DEVE ser informado como temporariamente indisponível, com sugestão de alternativas parecidas e disponíveis.
- **FR-011**: Produto descontinuado DEVE ser informado como fora do catálogo, com sugestão de equivalentes disponíveis.
- **FR-012**: Produto "em breve" DEVE ser informado como ainda não disponível para compra.
- **FR-013**: O agente DEVE informar a disponibilidade sem revelar a quantidade exata em estoque.
- **FR-014**: O agente DEVE responder apenas com o catálogo fornecido.

**Promoções e pagamento**

- **FR-015**: O agente DEVE considerar como ativa apenas a promoção marcada como ativa na fonte. As demais são tratadas como encerradas.
- **FR-016**: Preço promocional DEVE ser sempre mostrado junto do preço original e do percentual de desconto.
- **FR-017**: Ao ser perguntado sobre uma promoção vencida, o agente DEVE informar isso com transparência e mostrar o preço atual.
- **FR-018**: O agente DEVE aplicar 5% de desconto no PIX, sem acumular com promoção.
- **FR-019**: O parcelamento DEVE respeitar a parcela mínima de cada faixa do manual (2x e 3x: R$ 50; 4x a 6x: R$ 80; 7x a 12x: R$ 100). Quando a condição pedida não for possível, o agente DEVE indicar o maior parcelamento permitido.
- **FR-020**: Todos os valores informados DEVEM estar em reais, com precisão de centavos.

**Pedidos e privacidade**

- **FR-021**: Antes de mostrar qualquer dado de pedido, o agente DEVE confirmar a identidade com o número do pedido e mais um dado cadastrado (e-mail ou telefone).
- **FR-022**: A verificação DEVE ser aplicada pelo sistema, de modo que nenhuma mensagem do cliente consiga contorná-la.
- **FR-023**: O agente NUNCA DEVE revelar dados de outros clientes.
- **FR-024**: Falhas de confirmação e pedidos inexistentes DEVEM receber a mesma resposta, sem indicar se o pedido existe.
- **FR-025**: Após três falhas de confirmação na sessão, o agente DEVE parar de tentar e indicar o contato da loja.
- **FR-026**: A confirmação DEVE valer apenas para aquele pedido e aquela sessão.
- **FR-027**: O agente DEVE informar o status em linguagem natural (pendente, confirmado, enviado, entregue, cancelado), o código de rastreio e a previsão de entrega quando existirem, e o motivo quando o pedido foi cancelado.
- **FR-028**: O agente DEVE informar o total registrado no pedido, mesmo quando ele diferir da soma dos itens.
- **FR-029**: O agente DEVE mostrar somente os dados pessoais necessários para responder, conforme a seção de privacidade do manual.

**Trocas e devoluções**

- **FR-030**: O agente DEVE aplicar as regras do manual: arrependimento em 7 dias corridos após o recebimento, defeito em 30 dias corridos após a compra, troca por preferência em 7 dias, garantia legal de 90 dias após o recebimento e itens não elegíveis.
- **FR-031**: Quando houver pedido identificado e confirmado, o agente DEVE usar as datas dele para dizer se o cliente ainda está no prazo e até quando.
- **FR-032**: O último dia do prazo DEVE ser considerado dentro do prazo.
- **FR-033**: Quando faltar a data necessária para concluir, o agente NÃO DEVE concluir sobre o prazo e DEVE encaminhar para a equipe.

**Escopo, reclamações e encaminhamento**

- **FR-034**: Pedidos de acessórios (cordas, palhetas, cabos, cases, pedais, amplificadores) DEVEM ser redirecionados com educação, explicando que a loja vende exclusivamente instrumentos musicais.
- **FR-035**: Assuntos sem relação com a loja DEVEM receber recusa educada e convite para voltar ao tema.
- **FR-036**: Categorias sem produtos no catálogo (sopros e cordas orquestrais) DEVEM ser informadas como sem itens disponíveis no momento.
- **FR-037**: Ao receber uma reclamação, o agente DEVE acolher com empatia, obter um contato para retorno, registrar o resumo e informar que a equipe retorna em até 24 horas úteis.
- **FR-038**: Cada reclamação DEVE ficar registrada de forma que a equipe possa consultá-la depois do fim da sessão, com data, resumo e contato para retorno.
- **FR-039**: Dúvidas que exijam decisão da gerência ou que não estejam cobertas pelo manual DEVEM ser encaminhadas para atendimento humano, sem improviso.
- **FR-040**: O agente NÃO DEVE fechar vendas, emitir pagamento, alterar ou cancelar pedidos, nem calcular frete exato por CEP; DEVE orientar o cliente a procurar a loja ou informar as regras e prazos do manual.

**Uso, datas e entregáveis**

- **FR-041**: O agente DEVE poder ser usado por uma interface de texto simples, em terminal.
- **FR-042**: O agente PODE ser disponibilizado também para uso por outros sistemas, com o mesmo comportamento da interface de texto e sessões separadas.
- **FR-043**: A data de referência para prazos DEVE ser a data atual do sistema, com a possibilidade de fixar outra data em testes e demonstrações.
- **FR-044**: O projeto DEVE ser entregue em repositório Git público, com histórico real de commits, sem credenciais publicadas.
- **FR-045**: O projeto DEVE incluir um README com instruções de execução, justificativa das decisões técnicas, limitações conhecidas e uso de assistentes de IA.
- **FR-046**: O projeto DEVE incluir de 3 a 5 conversas de exemplo, ao menos uma não trivial (consulta a dados em tempo real ou aplicação de política).
- **FR-047**: Fora do horário de funcionamento, ao encaminhar o cliente para a equipe, o agente DEVE informar quando a equipe volta a atender.

### Key Entities *(include if feature involves data)*

- **Produto**: Instrumento do catálogo. Tem nome, categoria, preço, estoque, situação (ativo, descontinuado, em breve) e especificações.
- **Categoria**: Agrupa produtos por tipo de instrumento; pode estar sem produtos.
- **Promoção**: Desconto aplicado a um produto, com nome, percentual e indicação de ativa ou encerrada. Não tem datas de validade.
- **Pedido**: Compra de um cliente. Tem número, status, total registrado, datas, previsão de entrega, código de rastreio e motivo de cancelamento, quando existirem.
- **Item de pedido**: Produto, quantidade e valor dentro de um pedido.
- **Cliente**: Pessoa com nome, e-mail e telefone cadastrados; os dois últimos servem para confirmar identidade.
- **Política**: Seção do manual da loja (dados da loja, horários, pagamento, trocas e devoluções, frete, promoções, diretrizes de atendimento, garantia, privacidade).
- **Sessão de conversa**: Histórico de uma conversa e confirmações de identidade feitas nela; existe apenas durante a sessão.
- **Reclamação registrada**: Resumo da reclamação, data e contato para retorno, consultável pela equipe.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Os 7 cenários de aceite definidos para o projeto são atendidos em 100% das execuções da suíte de cenários.
- **SC-002**: Em um conjunto de pelo menos 30 perguntas sobre preço, estoque, promoção e política, 100% dos valores e regras informados coincidem com as fontes, sem nenhum dado inventado.
- **SC-003**: Em pelo menos 20 tentativas de obter dados de pedido sem confirmação válida, incluindo dados errados e tentativas de convencer o agente, nenhum dado de pedido ou de cliente é revelado.
- **SC-004**: 100% dos cálculos de PIX, promoção e parcelamento conferem ao centavo com as regras do manual em um conjunto de pelo menos 20 casos.
- **SC-005**: Pelo menos 90% de um conjunto de 20 variações de escrita (sem acento, com erro de digitação, nome parcial) levam ao produto certo ou a uma pergunta de confirmação que o inclui.
- **SC-006**: 100% dos casos de teste de prazo de troca e devolução, incluindo o último dia e o dia seguinte, chegam à conclusão correta.
- **SC-007**: Pelo menos 90% de 10 conversas com perguntas de seguimento são resolvidas sem que o cliente precise repetir o contexto.
- **SC-008**: Pelo menos 80% de um conjunto representativo de perguntas recorrentes é resolvido sem envolver a equipe, e todas as demais são encaminhadas com o contato da loja.
- **SC-009**: 95% das respostas chegam ao cliente em até 10 segundos.
- **SC-010**: Em revisão por uma pessoa da loja, pelo menos 90% das respostas de uma amostra de 20 são consideradas adequadas ao tom da Empório da Música.
- **SC-011**: Uma pessoa sem conhecimento prévio do projeto consegue iniciar uma conversa em até 15 minutos seguindo o README.

## Assumptions

- A data de referência para prazos é a data atual do sistema. Como os pedidos não têm data de recebimento, a previsão de entrega é usada como aproximação. Como o pedido entregue mais recente é de fevereiro de 2026, demonstrações de prazo aberto precisam fixar a data.
- Prazos que contam do recebimento: arrependimento e garantia legal. O prazo de defeito conta da data da compra, como diz o manual. O manual não define a base da troca por preferência; adota-se o recebimento.
- O direito de arrependimento é descrito no manual para compras online. Os dados não indicam o canal de venda; todos os pedidos são tratados como online.
- A fonte não permite verificar personalização nem aviso de "venda final". O agente explica essas exceções e pergunta ao cliente, sem concluir sozinho.
- O manual traz dois números de WhatsApp diferentes. O agente usa o telefone dos dados da empresa, (67) 3341-4444.
- O manual traz o e-mail da loja com e sem acento no domínio. O agente usa contato@emporiodamusica.com.br, da capa.
- O manual fala em parcelamento de até 12x com parcela mínima de R$ 100 na tabela e em faixas menores na seção 3.1. Vale a seção 3.1, mais específica. A compra em 1x no cartão não tem parcela mínima.
- Alguns pedidos históricos têm parcelas abaixo do mínimo atual (9, 16 e 18). O agente só informa o que está registrado.
- O manual sugere indicar lojas parceiras, mas não cita nenhuma. O agente não inventa parcerias.
- Os totais de alguns pedidos não batem com a soma dos itens (pedidos 3 e 20). O agente informa o total registrado no pedido.
- O manual cita mais de 300 instrumentos, mas o catálogo fornecido tem 65. O agente responde apenas com o catálogo fornecido.
- Depende dos arquivos de dados da operação (CSV) e do manual de políticas (PDF), disponíveis em `data/`.
- Em produto com promoção ativa, vale o preço promocional, sem os 5% do PIX, como diz a seção 6.2 do manual.
- Os dados de clientes são tratados como fictícios, pois os arquivos são de um desafio técnico e usam domínios de e-mail inexistentes. Por isso, podem ser publicados no repositório. Se forem reais, não podem ir para o repositório público nem aparecer nas conversas de exemplo.
- "Encaminhar para atendimento humano" significa orientar o cliente a falar com a equipe pelo contato da loja. Não há transferência automática da conversa nesta versão.
- O limite de três tentativas de confirmação, a lista de até 10 produtos, a ocultação da quantidade em estoque e a escolha da promoção de maior desconto são decisões padrão desta especificação, pois não constam do pedido original.
- O atendimento é somente leitura sobre os dados da operação; o único dado gravado pelo agente é o registro de reclamações.
- Os dados são lidos dos arquivos fornecidos, sem atualização durante a sessão.
- Integração real com WhatsApp está fora do escopo.
