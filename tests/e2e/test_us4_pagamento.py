import re


def test_preco_promocional_com_original_e_percentual(conversa, repo):
    resposta = conversa.enviar(f"Quanto custa o {repo.produto(121).nome}?")

    assert "439,20" in resposta
    assert "549,00" in resposta
    assert "20%" in resposta
    conversa.auditar_valores(resposta)


def test_pix_nao_acumula_e_explica(conversa, repo):
    resposta = conversa.enviar(
        f"Se eu pagar no PIX o {repo.produto(121).nome}, fica mais barato?"
    )

    assert "439,20" in resposta
    assert re.search(r"n[aã]o acumula|n[aã]o (se )?aplica|n[aã]o soma|n[aã]o tem", resposta)
    conversa.auditar_valores(resposta)


def test_parcelamento_impossivel_indica_o_maximo(conversa):
    resposta = conversa.enviar("Posso parcelar o Yamaha C40 em 12x?")

    assert "6x" in resposta or "6 vezes" in resposta
    conversa.auditar_valores(resposta)


def test_promocao_encerrada_mostra_o_preco_atual(conversa):
    resposta = conversa.enviar(
        "O Takamine GD20 ainda está na Oferta Especial? Quero o desconto."
    )

    assert "2.199,00" in resposta
    assert "1.935" not in resposta  # 12% de desconto já encerrado
    conversa.auditar_valores(resposta)


def test_campanha_encerrada_nao_e_prometida(conversa):
    resposta = conversa.enviar("Vocês estão com Black Friday?").lower()
    assert re.search(r"encerr|n[aã]o est[aá]|acabou|terminou|n[aã]o tem", resposta)
