def test_preco_e_pix_do_takamine(conversa):
    resposta = conversa.enviar("Quanto custa o Takamine GD20?")

    assert "detalhes_produto" in conversa.ferramentas
    assert "2.199,00" in resposta
    assert "2.089,05" in resposta
    conversa.auditar_valores(resposta)


def test_nome_sem_acento_e_aproximado(conversa):
    resposta = conversa.enviar("qto ta o violao takamin gd20?")
    assert "2.199,00" in resposta


def test_sem_estoque_sugere_alternativas(conversa):
    resposta = conversa.enviar("Quanto custa o Giannini GF-3D?")

    assert "indispon" in resposta.lower()
    assert conversa.resultados()[-1]["alternativas"]
    nomes = [a["nome"] for a in conversa.resultados()[-1]["alternativas"]]
    assert any(nome in resposta for nome in nomes)


def test_descontinuado(conversa):
    resposta = conversa.enviar("Tem o Shelby SN-7C?")
    assert "catálogo" in resposta.lower()


def test_em_breve(conversa):
    resposta = conversa.enviar("Quero o Kala KA-ABP-CTG")
    assert "disponível" in resposta.lower()


def test_produto_inexistente_oferece_contato(conversa):
    resposta = conversa.enviar("Quanto custa a Gibson Flying V Zebrada?")
    assert "3341-4444" in resposta
    conversa.auditar_valores(resposta)
