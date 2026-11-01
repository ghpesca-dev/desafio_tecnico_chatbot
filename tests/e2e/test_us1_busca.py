import pytest


def test_violoes_ate_1000(conversa, repo):
    resposta = conversa.enviar("Quais violões vocês têm até R$ 1000?")

    assert "buscar_produtos" in conversa.ferramentas
    assert "R$" in resposta
    conversa.auditar_valores(resposta)
    # Produto 96 está sem estoque e 113 foi descontinuado.
    assert "GF-3D" not in resposta
    assert "SN-7C" not in resposta


@pytest.mark.parametrize(
    "pergunta",
    ["Vocês têm saxofone?", "Tem flauta?", "Vocês vendem violino?"],
)
def test_categoria_sem_produtos(conversa, pergunta):
    resposta = conversa.enviar(pergunta).lower()

    assert "buscar_produtos" in conversa.ferramentas
    assert "momento" in resposta
    assert "r$" not in resposta
    # Sopros e cordas orquestrais são instrumentos, não acessórios.
    assert "exclusivamente" not in resposta
    assert "só com instrumentos" not in resposta
    assert "apenas com instrumentos" not in resposta


def test_lista_nao_faz_afirmacao_sem_fonte(conversa):
    resposta = conversa.enviar("Quais violões vocês têm até R$ 1000?").lower()

    assert "mais vendid" not in resposta
    assert "mais procurad" not in resposta
    assert "macio" not in resposta
    assert "12" in resposta  # total_encontrado


def test_alternativa_em_promocao_mostra_preco_original(conversa):
    conversa.enviar("Quanto custa o Takamine GD20?")
    resposta = conversa.enviar("tem outro parecido?")

    # Crafter HT-100, de R$ 2.399,00 por R$ 1.967,18, é uma das alternativas.
    assert "1.967,18" in resposta
    assert "2.399,00" in resposta
    assert "18%" in resposta
    assert "1.899,00" in resposta  # Yamaha APX600
    assert "2.499,00" in resposta  # Takamine GC1CE
