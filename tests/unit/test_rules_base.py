from decimal import Decimal as D

import pytest

from emporio.rules import (
    calcular_pix,
    formatar_brl,
    normalizar,
    preco_atual,
    situacao_produto,
)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (D("1234.56"), "R$ 1.234,56"),
        (D("323.1"), "R$ 323,10"),
        (D("19567"), "R$ 19.567,00"),
        (D("0.005"), "R$ 0,01"),
        (D("1000000"), "R$ 1.000.000,00"),
    ],
)
def test_formatar_brl(valor, esperado):
    assert formatar_brl(valor) == esperado


@pytest.mark.parametrize(
    ("preco", "desconto", "esperado"),
    [
        (D("359"), D("10"), "R$ 323,10"),  # produto 127
        (D("549"), D("20"), "R$ 439,20"),  # produto 121
        (D("2399"), D("18"), "R$ 1.967,18"),  # produto 90
        (D("5999"), D("8"), "R$ 5.519,08"),  # produto 94
        (D("2199"), None, "R$ 2.199,00"),  # sem promoção
    ],
)
def test_preco_atual(preco, desconto, esperado):
    assert formatar_brl(preco_atual(preco, desconto)) == esperado


def test_pix_sem_promocao_tem_5_por_cento_sobre_tabela():
    pix = calcular_pix(D("2199"), None)
    assert formatar_brl(pix.valor) == "R$ 2.089,05"
    assert pix.nao_acumula is False


def test_pix_nao_acumula_com_promocao():
    pix = calcular_pix(D("359"), D("10"))
    assert formatar_brl(pix.valor) == "R$ 323,10"
    assert pix.nao_acumula is True


@pytest.mark.parametrize(
    ("status", "estoque", "preco", "esperado"),
    [
        ("active", 5, D("100"), "disponivel"),
        ("active", 0, D("799.9"), "temporariamente_indisponivel"),  # produto 96
        ("discontinued", 0, D("749"), "fora_de_catalogo"),  # produto 113
        ("discontinued", 13, D("441"), "fora_de_catalogo"),  # produto 136
        ("coming_soon", 2, D("1749"), "em_breve"),  # produto 130
        ("active", 5, None, "sem_informacao"),
    ],
)
def test_situacao_produto(status, estoque, preco, esperado):
    assert situacao_produto(status, estoque, preco) == esperado


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Violões", "violoes"),
        ("Takamine GD-20", "takamine gd20"),
        ("  KA-ABP-CTG   Barítono ", "kaabpctg baritono"),
    ],
)
def test_normalizar(texto, esperado):
    assert normalizar(texto) == esperado
