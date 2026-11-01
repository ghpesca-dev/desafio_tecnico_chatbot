import json
from datetime import date, datetime, timezone

import pytest

from emporio.complaints import Reclamacoes
from emporio.session import SessionState
from emporio.tools import REGISTRO, Contexto

MOMENTO = datetime(2026, 2, 20, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def reclamacoes(tmp_path):
    return Reclamacoes(tmp_path / "runtime" / "reclamacoes.jsonl")


def registrar(reclamacoes, resumo="Demorou", contato="maria@teste.com", **extra):
    return reclamacoes.registrar(
        sessao_id="s1", resumo=resumo, contato=contato, momento=MOMENTO, **extra
    )


def chamar(reclamacoes, **args):
    contexto = Contexto(
        None,
        SessionState(id="s1"),
        date(2026, 2, 20),
        reclamacoes=reclamacoes,
        agora=MOMENTO,
    )
    return json.loads(
        REGISTRO.despachar("registrar_reclamacao", json.dumps(args), contexto)
    )


def test_grava_os_campos_do_modelo(reclamacoes):
    registrar(reclamacoes, nome="Maria", pedido=8)

    linha = json.loads(reclamacoes.caminho.read_text(encoding="utf-8"))
    assert linha["id"]
    assert linha["registrada_em"] == MOMENTO.isoformat()
    assert linha["sessao_id"] == "s1"
    assert linha["resumo"] == "Demorou"
    assert linha["contato"] == "maria@teste.com"
    assert linha["nome"] == "Maria"
    assert linha["pedido"] == 8


@pytest.mark.parametrize("campo", ["resumo", "contato"])
@pytest.mark.parametrize("valor", ["", "   "])
def test_campos_obrigatorios_nao_vazios(reclamacoes, campo, valor):
    with pytest.raises(ValueError):
        registrar(reclamacoes, **{campo: valor})
    assert not reclamacoes.caminho.exists()


def test_so_acrescenta(reclamacoes):
    registrar(reclamacoes, resumo="Primeira")
    registrar(reclamacoes, resumo="Segunda")
    assert len(reclamacoes.caminho.read_text(encoding="utf-8").splitlines()) == 2


def test_lista_da_mais_recente_para_a_mais_antiga(reclamacoes):
    registrar(reclamacoes, resumo="Primeira")
    registrar(reclamacoes, resumo="Segunda")
    assert [r.resumo for r in reclamacoes.listar()] == ["Segunda", "Primeira"]


def test_lista_vazia_sem_arquivo(reclamacoes):
    assert reclamacoes.listar() == []


def test_linha_quebrada_nao_impede_a_listagem(reclamacoes):
    registrar(reclamacoes)
    with reclamacoes.caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write("quebrada\n")
    assert len(reclamacoes.listar()) == 1


def test_ferramenta_devolve_o_protocolo(reclamacoes):
    resultado = chamar(reclamacoes, resumo="Demorou", contato="67999990000")

    assert resultado["registrada"] is True
    assert resultado["protocolo"] == reclamacoes.listar()[0].id


def test_falha_de_escrita_retorna_registrada_falso(tmp_path):
    bloqueio = tmp_path / "arquivo"
    bloqueio.write_text("x", encoding="utf-8")
    resultado = chamar(
        Reclamacoes(bloqueio / "reclamacoes.jsonl"),
        resumo="Demorou",
        contato="67999990000",
    )

    assert resultado["registrada"] is False
    assert resultado["protocolo"] is None


@pytest.mark.parametrize(
    "args",
    [{"resumo": "", "contato": "x"}, {"resumo": "x", "contato": " "}, {"resumo": "x"}],
)
def test_ferramenta_recusa_sem_campos_obrigatorios(reclamacoes, args):
    assert "erro" in chamar(reclamacoes, **args)
    assert reclamacoes.listar() == []
