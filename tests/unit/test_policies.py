import json
from datetime import date

import pytest

from emporio.config import PASTA_POLITICAS
from emporio.policies import TOPICOS, Politicas, PoliticasInvalidas
from emporio.session import SessionState
from emporio.tools import REGISTRO, Contexto


@pytest.fixture(scope="module")
def politicas():
    return Politicas(PASTA_POLITICAS)


def consultar(politicas, topico):
    contexto = Contexto(None, SessionState(), date(2026, 2, 20), politicas)
    return json.loads(
        REGISTRO.despachar(
            "consultar_politica", json.dumps({"topico": topico}), contexto
        )
    )


def test_todos_os_topicos_existem_e_nao_estao_vazios(politicas):
    assert len(TOPICOS) == 9
    for topico in TOPICOS:
        assert len(politicas.texto(topico)) > 100


@pytest.mark.parametrize("topico", TOPICOS)
def test_nenhum_topico_contradiz_a_spec(politicas, topico):
    texto = politicas.texto(topico)
    assert "3321-4500" not in texto
    assert "empóriodamusica" not in texto
    assert "mais de 300" not in texto


def test_loja_tem_contato_e_endereco(politicas):
    texto = politicas.texto("loja")
    assert "(67) 3341-4444" in texto
    assert "Rua 14 de Maio, 3200" in texto
    assert "contato@emporiodamusica.com.br" in texto


def test_pagamento_nao_exige_100_em_todo_parcelamento(politicas):
    texto = politicas.texto("pagamento")
    linha = next(i for i in texto.splitlines() if "Cartão de Crédito" in i)
    assert "R$ 100,00" not in linha
    assert "R$ 80,00" in texto
    assert "R$ 50,00" in texto


@pytest.mark.parametrize(
    ("topico", "trecho"),
    [
        ("horario", "09:00 às 18:00"),
        ("horario", "09:00 às 13:00"),
        ("pagamento", "5% de desconto"),
        ("trocas_devolucoes", "7 (sete) dias corridos"),
        ("trocas_devolucoes", "30 (trinta) dias corridos"),
        ("trocas_devolucoes", "Boquilhas"),
        ("frete", "R$ 500,00"),
        ("frete", "SEDEX"),
        ("promocoes", "não são cumulativas"),
        ("atendimento", "24 horas úteis"),
        ("atendimento", "consultar a gerência"),
        ("garantia", "90"),
        ("privacidade", "LGPD"),
    ],
)
def test_conteudo_por_topico(politicas, topico, trecho):
    assert trecho in politicas.texto(topico)


def test_sem_cabecalho_nem_rodape(politicas):
    for topico in TOPICOS:
        texto = politicas.texto(topico)
        assert "Manual de Políticas e Procedimentos" not in texto
        assert "Página " not in texto


def test_ferramenta_devolve_o_texto(politicas):
    resultado = consultar(politicas, "horario")
    assert resultado["topico"] == "horario"
    assert "09:00 às 18:00" in resultado["texto"]


def test_topico_invalido_retorna_erro(politicas):
    assert "erro" in consultar(politicas, "receita_de_bolo")


def test_schema_usa_enum_de_topicos():
    schema = next(
        s["function"]["parameters"]
        for s in REGISTRO.schemas()
        if s["function"]["name"] == "consultar_politica"
    )
    assert "horario" in json.dumps(schema)


def test_arquivo_faltando_interrompe(tmp_path):
    with pytest.raises(PoliticasInvalidas):
        Politicas(tmp_path)


def test_arquivo_vazio_interrompe(tmp_path):
    for topico in TOPICOS:
        (tmp_path / f"{topico}.md").write_text("conteúdo", encoding="utf-8")
    (tmp_path / "frete.md").write_text("  \n", encoding="utf-8")

    with pytest.raises(PoliticasInvalidas) as erro:
        Politicas(tmp_path)

    assert "frete" in str(erro.value)
