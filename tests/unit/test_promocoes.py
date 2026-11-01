import json
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from emporio.data.repository import Repository
from emporio.session import SessionState
from emporio.tools import REGISTRO, Contexto


@pytest.fixture
def chamar(repo):
    def _chamar(ferramenta, **args):
        contexto = Contexto(repo, SessionState(), date(2026, 2, 20))
        return json.loads(REGISTRO.despachar(ferramenta, json.dumps(args), contexto))

    return _chamar


def test_quatro_produtos_com_promocao_ativa(repo):
    ativos = {p.id for p in repo.produtos() if p.promocao_ativa}
    assert ativos == {90, 94, 121, 127}


def test_duas_ativas_usam_o_maior_desconto(dados):
    extra = pd.DataFrame(
        [
            {
                "promotion_id": 99,
                "product_id": 121,
                "discount_percent": Decimal("30"),
                "description": "Maior",
                "is_active": True,
            }
        ]
    )
    promocoes = pd.concat([dados.promocoes, extra], ignore_index=True)
    produto = Repository(replace(dados, promocoes=promocoes)).produto(121)

    assert produto.promocao_ativa.nome == "Maior"
    assert produto.preco_atual == Decimal("384.30")


def test_encerrada_aparece_nos_detalhes(chamar):
    produto = chamar("detalhes_produto", referencia="95")["produto"]

    assert produto["promocao_ativa"] is None
    assert produto["promocao_encerrada"]["nome"] == "Oferta Especial"
    assert produto["preco_atual"] == "R$ 2.199,00"


def test_varias_encerradas_usam_a_mais_recente(repo):
    assert repo.produto(96).promocao_encerrada.id == 22


def test_promocao_ativa_nao_traz_encerrada(chamar):
    produto = chamar("detalhes_produto", referencia="121")["produto"]
    assert produto["promocao_ativa"]["nome"] == "Desconto Exclusivo"
    assert produto["promocao_encerrada"] is None


def test_em_promocao_lista_as_ativas(chamar):
    resultado = chamar("buscar_produtos", em_promocao=True)
    assert {p["id"] for p in resultado["produtos"]} == {90, 94, 121, 127}


def test_em_promocao_combina_com_categoria(chamar):
    resultado = chamar("buscar_produtos", em_promocao=True, categoria="ukulele")
    assert {p["id"] for p in resultado["produtos"]} == {121, 127}


def test_nome_de_promocao_encerrada(chamar):
    resultado = chamar("buscar_produtos", texto="Black Friday")

    assert resultado["promocao_encontrada"] == {
        "nome": "Black Friday",
        "ativa": False,
    }
    assert resultado["produtos"] == []
    assert resultado["orientacao"] is None


def test_nome_de_promocao_ativa_lista_os_produtos(chamar):
    resultado = chamar("buscar_produtos", texto="desconto exclusivo")

    assert resultado["promocao_encontrada"]["ativa"] is True
    assert {p["id"] for p in resultado["produtos"]} == {90, 94, 121}


def test_nome_ativo_e_encerrado_conta_como_ativa(chamar):
    # `Oferta Especial` está encerrada no 95, mas ativa no 127.
    resultado = chamar("buscar_produtos", texto="Oferta Especial")

    assert resultado["promocao_encontrada"]["ativa"] is True
    assert {p["id"] for p in resultado["produtos"]} == {127}


def test_busca_comum_nao_traz_promocao(chamar):
    assert chamar("buscar_produtos", texto="takamine")["promocao_encontrada"] is None


def test_pagamento_traz_parcelas_do_preco_atual(chamar):
    pagamento = chamar("detalhes_produto", referencia="121")["pagamento"]

    assert pagamento["max_parcelas"] == 5
    assert pagamento["parcelas_sem_juros"] is True
    assert pagamento["parcelas"][0] == {"vezes": 1, "valor": "R$ 439,20"}
    assert pagamento["parcelas"][-1] == {"vezes": 5, "valor": "R$ 87,84"}


def test_em_breve_nao_tem_pagamento(chamar):
    assert chamar("detalhes_produto", referencia="130")["pagamento"] is None
