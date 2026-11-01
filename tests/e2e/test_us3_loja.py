import pytest

FERRAMENTAS_DE_PRODUTO = {"buscar_produtos", "detalhes_produto"}


def test_endereco_nao_consulta_produtos(conversa):
    resposta = conversa.enviar("Qual o endereço da loja?")

    assert "consultar_politica" in conversa.ferramentas
    assert not FERRAMENTAS_DE_PRODUTO & set(conversa.ferramentas)
    assert "14 de Maio" in resposta
    assert "3200" in resposta


@pytest.mark.parametrize(
    ("pergunta", "trecho"),
    [
        ("Que horas vocês abrem no sábado?", "13"),
        ("Qual o telefone de vocês?", "3341-4444"),
        ("A partir de quanto o frete é grátis em Campo Grande?", "500"),
        ("Quanto tempo de garantia legal tem um instrumento?", "90"),
    ],
)
def test_informacoes_do_manual(conversa, pergunta, trecho):
    resposta = conversa.enviar(pergunta)

    assert "consultar_politica" in conversa.ferramentas
    assert trecho in resposta


def test_frete_por_cep_nao_informa_valor_exato(conversa):
    resposta = conversa.enviar("Quanto fica o frete para o CEP 01310-100?")

    assert "consultar_politica" in conversa.ferramentas
    conversa.auditar_valores(resposta)
