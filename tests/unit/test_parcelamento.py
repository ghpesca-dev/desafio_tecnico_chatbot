from decimal import Decimal

import pytest

from emporio.rules import formatar_brl, tabela_parcelas


@pytest.mark.parametrize(
    ("preco", "maximo"),
    [
        ("2199.00", 12),
        ("323.10", 4),
        ("439.20", 5),
        ("159.90", 3),
        ("599.90", 6),
        ("800.00", 8),
        ("90.00", 1),
        ("1.00", 1),
        ("49.00", 1),
        ("99.99", 1),  # 2x daria R$ 49,995
        ("100.00", 2),
        ("149.99", 2),
        ("150.00", 3),
        ("319.99", 3),  # 4x daria R$ 79,9975
        ("320.00", 4),
        ("400.00", 5),
        ("480.00", 6),
        ("699.99", 6),
        ("700.00", 7),
        ("799.99", 7),  # 8x arredondaria para R$ 100,00, mas é menos que isso
        ("1199.99", 11),
        ("1200.00", 12),
        ("5000.00", 12),
    ],
)
def test_maximo_de_parcelas(preco, maximo):
    assert tabela_parcelas(Decimal(preco)).max_parcelas == maximo


def test_parcelas_vao_de_1x_ao_maximo():
    tabela = tabela_parcelas(Decimal("439.20"))
    assert [p.vezes for p in tabela.parcelas] == [1, 2, 3, 4, 5]


def test_valor_de_cada_parcela():
    tabela = tabela_parcelas(Decimal("2199.00"))
    assert formatar_brl(tabela.parcelas[0].valor) == "R$ 2.199,00"
    assert formatar_brl(tabela.parcelas[11].valor) == "R$ 183,25"


def test_valor_da_parcela_e_arredondado_ao_centavo():
    tabela = tabela_parcelas(Decimal("100.00"))
    assert formatar_brl(tabela.parcelas[1].valor) == "R$ 50,00"
    tabela = tabela_parcelas(Decimal("200.00"))
    assert formatar_brl(tabela.parcelas[2].valor) == "R$ 66,67"
