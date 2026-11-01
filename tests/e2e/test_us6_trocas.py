import re


def email_do_pedido(dados, numero):
    pedido = dados.pedidos[dados.pedidos["order_id"] == numero].iloc[0]
    cliente = dados.clientes[dados.clientes["customer_id"] == pedido["customer_id"]]
    return cliente.iloc[0]["email"]


def test_arrependimento_no_prazo(conversa, dados):
    resposta = conversa.enviar("Me arrependi da compra, posso devolver?").lower()
    assert "pedido" in resposta

    resposta = conversa.enviar(
        f"Pedido 7, e-mail {email_do_pedido(dados, 7)}"
    ).lower()

    assert "consultar_pedido" in conversa.ferramentas
    assert "24/02" in resposta or "24 de fevereiro" in resposta


def test_arrependimento_fora_do_prazo(conversa, dados):
    conversa.enviar("Me arrependi da compra, posso devolver?")
    resposta = conversa.enviar(
        f"Pedido 6, e-mail {email_do_pedido(dados, 6)}"
    ).lower()

    assert "08/02" in resposta or "8 de fevereiro" in resposta
    assert re.search(r"encerr|fora do prazo|passou|venceu|expirou|terminou", resposta)


def test_sem_pedido_explica_a_regra_geral(conversa):
    resposta = conversa.enviar("Quais são as regras para devolver um produto?")

    assert "consultar_politica" in conversa.ferramentas
    assert "7" in resposta


def test_prazo_indeterminado_encaminha(conversa_incompleta):
    resposta = conversa_incompleta.enviar(
        "Me arrependi. Pedido 1, e-mail maria@teste.com. Ainda dá para devolver?"
    )

    assert "3341-4444" in resposta
    assert "no prazo" not in resposta.lower().replace("não está no prazo", "")


def test_defeito_depois_de_30_dias_indica_garantia(conversa, dados):
    resposta = conversa.enviar(
        f"Meu instrumento veio com defeito. Pedido 6, e-mail "
        f"{email_do_pedido(dados, 6)}. Posso trocar?"
    ).lower()

    assert "garantia" in resposta or "fabricante" in resposta
