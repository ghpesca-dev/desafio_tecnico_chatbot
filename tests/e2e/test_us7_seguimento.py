import pytest

from emporio.rules import calcular_pix, formatar_brl


def pix(repo, numero):
    produto = repo.produto(numero)
    promocao = produto.promocao_ativa
    valor = calcular_pix(produto.preco, promocao.desconto if promocao else None).valor
    return formatar_brl(valor).removeprefix("R$ ")


def email_do_pedido(dados, numero):
    pedido = dados.pedidos[dados.pedidos["order_id"] == numero].iloc[0]
    cliente = dados.clientes[dados.clientes["customer_id"] == pedido["customer_id"]]
    return cliente.iloc[0]["email"]


@pytest.mark.parametrize(
    ("primeira", "seguimento", "esperado"),
    [
        ("Quanto custa o Takamine GD20?", "e no PIX?", ["2.089,05"]),
        (
            "Quanto custa o Takamine GD20?",
            "tem outro parecido?",
            ["1.967,18", "1.899,00", "2.499,00"],
        ),
        ("Quanto custa o Takamine GD20?", "em quantas vezes sem juros?", ["12"]),
        ("Quanto custa o Takamine GD20?", "e o Yamaha C40?", ["599,90"]),
        ("Quanto custa o Yamaha C40?", "e no PIX?", ["569,91"]),
        ("Qual o endereço da loja?", "e abre no sábado?", ["13"]),
        ("Quais violões vocês têm até R$ 1000?", "e o mais barato, quanto é?", ["429,90"]),
    ],
)
def test_seguimento_sem_repetir_o_contexto(conversa, primeira, seguimento, esperado):
    conversa.enviar(primeira)
    resposta = conversa.enviar(seguimento)

    for trecho in esperado:
        assert trecho in resposta
    assert "corrigir" not in resposta.lower()


def test_parecido_com_produto_sem_estoque(conversa):
    conversa.enviar("Quanto custa o Giannini GF-3D?")
    resposta = conversa.enviar("tem outro parecido?")

    alternativas = conversa.resultados()[0]["alternativas"]
    assert any(a["nome"] in resposta for a in alternativas)


def test_pix_de_produto_em_promocao_no_seguimento(conversa, repo):
    conversa.enviar(f"Quanto custa o {repo.produto(121).nome}?")
    resposta = conversa.enviar("e no PIX?")

    assert pix(repo, 121) in resposta


def test_pedido_confirmado_nao_pede_contato_de_novo(conversa, dados):
    conversa.enviar(f"Pedido 8, e-mail {email_do_pedido(dados, 8)}. Qual o status?")
    resposta = conversa.enviar("e quando chega?")

    assert "28/02" in resposta or "28 de fevereiro" in resposta
