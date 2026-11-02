"""Histórico de conversas em arquivos JSON."""

import json
import uuid

import pytest

from emporio.historico import Historico


def novo_id():
    return str(uuid.uuid4())


def gravar(historico, conversa_id=None, texto="oi", momento="2026-11-01T10:00:00-04:00",
           consultas=()):
    conversa_id = conversa_id or novo_id()
    historico.registrar_troca(
        conversa_id,
        texto=texto,
        resposta="Olá!",
        momento_cliente=momento,
        momento_agente=momento,
        tempo_ms=100,
        consultas=list(consultas),
    )
    return conversa_id


@pytest.fixture
def historico(tmp_path):
    return Historico(tmp_path / "conversas")


def test_pasta_ausente_lista_vazia(historico):
    assert historico.listar() == []


def test_grava_e_le_uma_troca(historico):
    consulta = {"nome": "buscar_produtos", "parametros": "{}", "duracao_ms": 1.5}
    conversa_id = gravar(historico, texto="Tem violão?", consultas=[consulta])

    conversa = historico.obter(conversa_id)

    assert conversa["id"] == conversa_id
    assert conversa["titulo"] == "Tem violão?"
    cliente, agente = conversa["mensagens"]
    assert (cliente["autor"], cliente["texto"]) == ("cliente", "Tem violão?")
    assert (agente["autor"], agente["texto"]) == ("agente", "Olá!")
    assert agente["tempo_ms"] == 100
    assert agente["consultas"] == [consulta]
    assert "consultas" not in cliente


def test_nova_troca_acrescenta_e_mantem_titulo(historico):
    conversa_id = gravar(historico, texto="primeira", momento="2026-11-01T10:00:00-04:00")
    gravar(historico, conversa_id, texto="segunda", momento="2026-11-01T11:00:00-04:00")

    conversa = historico.obter(conversa_id)

    assert conversa["titulo"] == "primeira"
    assert len(conversa["mensagens"]) == 4
    assert conversa["iniciada_em"] == "2026-11-01T10:00:00-04:00"
    assert conversa["atualizada_em"] == "2026-11-01T11:00:00-04:00"


def test_titulo_cortado_em_60_caracteres(historico):
    conversa_id = gravar(historico, texto="a" * 200)
    assert len(historico.obter(conversa_id)["titulo"]) == 60


def test_lista_da_mais_recente_para_a_mais_antiga(historico):
    antiga = gravar(historico, momento="2026-11-01T09:00:00-04:00")
    recente = gravar(historico, momento="2026-11-01T12:00:00-04:00")

    assert [c["id"] for c in historico.listar()] == [recente, antiga]


@pytest.mark.parametrize(
    "invalido",
    ["inventado", "../../.env", "..", "", "A" * 36, "{" + str(uuid.uuid4()) + "}"],
)
def test_id_invalido_nao_toca_no_disco(historico, invalido):
    gravar(historico)

    assert historico.obter(invalido) is None
    assert historico.remover(invalido) is False


def test_id_invalido_nao_grava(historico):
    with pytest.raises(ValueError):
        gravar(historico, "../fora")
    assert historico.listar() == []


def test_arquivo_danificado_nao_afeta_os_outros(historico, caplog):
    boa = gravar(historico)
    (historico.pasta / f"{novo_id()}.json").write_text("{quebrado", encoding="utf-8")
    (historico.pasta / f"{novo_id()}.json").write_text("[]", encoding="utf-8")
    (historico.pasta / f"{novo_id()}.json").write_text(
        json.dumps({"id": "outro", "mensagens": []}), encoding="utf-8"
    )

    with caplog.at_level("WARNING", logger="emporio.historico"):
        assert [c["id"] for c in historico.listar()] == [boa]
    assert "ignorado" in caplog.text


def test_nao_deixa_temporarios(historico):
    gravar(historico)
    assert [p.suffix for p in historico.pasta.iterdir()] == [".json"]


def test_remover(historico):
    conversa_id = gravar(historico)

    assert historico.remover(conversa_id) is True
    assert historico.obter(conversa_id) is None
    assert historico.remover(conversa_id) is False


def test_indicadores_vazios(historico):
    assert historico.indicadores([]) == {
        "conversas": 0,
        "mensagens_cliente": 0,
        "tempo_medio_ms": 0,
        "consultas_mais_usadas": [],
    }


def test_indicadores(historico):
    consulta = {"nome": "buscar_produtos", "parametros": "{}", "duracao_ms": 1}
    outra = {"nome": "consultar_politica", "parametros": "{}", "duracao_ms": 1}
    primeira = gravar(historico, consultas=[consulta, consulta, outra])
    gravar(historico, primeira)
    gravar(historico)

    assert historico.indicadores(historico.listar()) == {
        "conversas": 2,
        "mensagens_cliente": 3,
        "tempo_medio_ms": 100,
        "consultas_mais_usadas": [
            {"nome": "buscar_produtos", "total": 2},
            {"nome": "consultar_politica", "total": 1},
        ],
    }


def test_indicadores_mostram_ate_3_consultas(historico):
    consultas = [
        {"nome": nome, "parametros": "{}", "duracao_ms": 1} for nome in "abcd"
    ]
    gravar(historico, consultas=consultas)

    assert len(historico.indicadores(historico.listar())["consultas_mais_usadas"]) == 3
