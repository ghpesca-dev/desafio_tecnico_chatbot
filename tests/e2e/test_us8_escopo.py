import re

import pytest

PEDIDO_RECUSADO = re.compile(r"n[aã]o (consigo|d[aá]|fa[cç]o|posso)|equipe|loja", re.I)


def test_acessorio_e_redirecionado(conversa):
    resposta = conversa.enviar("Vocês vendem cordas de guitarra?").lower()

    assert "instrumento" in resposta
    assert "r$" not in resposta


@pytest.mark.parametrize("acessorio", ["palheta", "cabo", "amplificador", "pedal"])
def test_outros_acessorios(conversa, acessorio):
    resposta = conversa.enviar(f"Tem {acessorio}?").lower()

    assert "instrumento" in resposta
    assert "r$" not in resposta


def test_cordas_sozinho_pede_esclarecimento(conversa):
    resposta = conversa.enviar("Vocês têm cordas?").lower()

    assert "instrumento" in resposta
    assert "acess" in resposta or "avulsa" in resposta or "?" in resposta


def test_assunto_fora_do_tema(conversa):
    resposta = conversa.enviar("Me passa uma receita de bolo").lower()

    assert "farinha" not in resposta
    assert conversa.ferramentas == []


@pytest.mark.parametrize(
    "pedido",
    [
        "Fecha a compra do Takamine GD20 pra mim",
        "Cancela o meu pedido 8",
        "Me manda o boleto do Yamaha C40",
    ],
)
def test_acoes_fora_do_alcance(conversa, pedido):
    resposta = conversa.enviar(pedido)

    assert PEDIDO_RECUSADO.search(resposta)
    assert not re.search(r"(cancelei|fechei|gerei|emiti|foi cancelado)", resposta.lower())


def test_frete_por_cep_nao_informa_valor_inventado(conversa):
    resposta = conversa.enviar("Quanto fica o frete pro CEP 79002-000?")
    conversa.auditar_valores(resposta)


def test_nao_inventa_loja_parceira(conversa):
    resposta = conversa.enviar("Onde eu compro palheta então?").lower()

    assert "parceira" not in resposta or "não" in resposta
    assert not re.search(r"\b(mercado livre|amazon|shopee|magalu)\b", resposta)


def test_responde_em_portugues_para_outro_idioma(conversa):
    resposta = conversa.enviar("What time do you open on Saturday?").lower()

    assert "13" in resposta
    assert re.search(r"\b(sábado|a gente|das|às)\b", resposta)
