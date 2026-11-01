def test_violoes_ate_1000(conversa, repo):
    resposta = conversa.enviar("Quais violões vocês têm até R$ 1000?")

    assert "buscar_produtos" in conversa.ferramentas
    assert "R$" in resposta
    conversa.auditar_valores(resposta)
    # Produto 96 está sem estoque e 113 foi descontinuado.
    assert "GF-3D" not in resposta
    assert "SN-7C" not in resposta


def test_categoria_sem_produtos(conversa):
    resposta = conversa.enviar("Vocês têm saxofone?")

    assert "buscar_produtos" in conversa.ferramentas
    assert "momento" in resposta.lower()
    assert "R$" not in resposta
