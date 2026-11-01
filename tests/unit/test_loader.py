import shutil
from decimal import Decimal as D
from pathlib import Path

import pytest

from emporio.data.loader import PREFIXO, DadosInvalidos, carregar_dados

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_carrega_todas_as_tabelas(dados):
    assert len(dados.produtos) == 65
    assert len(dados.categorias) == 9
    assert len(dados.promocoes) == 25
    assert len(dados.pedidos) == 20
    assert len(dados.itens) == 22
    assert len(dados.clientes) == 50


def test_converte_tipos(dados):
    produto = dados.produtos.set_index("product_id").loc[95]
    assert produto["price_brl"] == D("2199")
    assert produto["categoria"] == "Violões"
    assert isinstance(produto["specs"], dict)
    assert produto["nome_normalizado"] == "takamine gd20 dreadnought natural"
    pedido = dados.pedidos.set_index("order_id").loc[4]
    assert pedido["total_brl"] == D("799.9")


def test_todos_os_specs_reais_sao_validos(dados):
    assert all(isinstance(s, dict) for s in dados.produtos["specs"])
    assert not any("specs" in a for a in dados.avisos)


def test_aviso_de_divergencia_so_nos_pedidos_3_e_20(dados):
    divergentes = [a for a in dados.avisos if "difere da soma" in a]
    assert len(divergentes) == 2
    assert any("Pedido 3:" in a for a in divergentes)
    assert any("Pedido 20:" in a for a in divergentes)


def test_dados_reais_nao_geram_outros_avisos(dados):
    assert [a for a in dados.avisos if "difere da soma" not in a] == []


def test_fixture_avisa_specs_invalido_e_vira_dicionario_vazio(dados_fixture):
    produto = dados_fixture.produtos.set_index("product_id").loc[3]
    assert produto["specs"] == {}
    assert any("Produto 3" in a and "specs" in a for a in dados_fixture.avisos)


def test_fixture_avisa_referencia_quebrada_e_marca_incompleto(dados_fixture):
    produto = dados_fixture.produtos.set_index("product_id").loc[4]
    assert bool(produto["dados_incompletos"]) is True
    assert any("Produto 4" in a and "categoria" in a for a in dados_fixture.avisos)


def test_fixture_produto_sem_preco_nao_recebe_valor(dados_fixture):
    produto = dados_fixture.produtos.set_index("product_id").loc[2]
    assert produto["price_brl"] is None
    assert bool(produto["dados_incompletos"]) is True
    assert any("Produto 2" in a and "preço" in a for a in dados_fixture.avisos)


def test_avisa_catalogo_com_tamanho_inesperado(dados_fixture):
    assert any("65" in a for a in dados_fixture.avisos)


def test_coluna_faltando_interrompe_com_a_lista(tmp_path):
    for arquivo in FIXTURES.glob("*.csv"):
        shutil.copy(arquivo, tmp_path)
    alvo = tmp_path / f"{PREFIXO}promotions.csv"
    alvo.write_text("promotion_id,product_id\n1,1\n", encoding="utf-8")

    with pytest.raises(DadosInvalidos) as erro:
        carregar_dados(tmp_path)

    assert "discount_percent" in str(erro.value)
    assert "is_active" in str(erro.value)


def test_arquivo_faltando_interrompe(tmp_path):
    with pytest.raises(DadosInvalidos):
        carregar_dados(tmp_path)
