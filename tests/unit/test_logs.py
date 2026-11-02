"""O log de depuração não pode guardar dados de contato."""

from datetime import date, datetime
from types import SimpleNamespace as NS
import json

import pytest

from emporio.agent import Agent, mascarar_argumentos
from emporio.config import Config
from emporio.session import SessionState
from emporio.tools import REGISTRO


def resposta(mensagem):
    return NS(choices=[NS(message=mensagem)])


def chamada(contato):
    argumentos = json.dumps({"numero_pedido": 8, "contato": contato})
    calls = [
        NS(
            id="c0",
            type="function",
            function=NS(name="consultar_pedido", arguments=argumentos),
        )
    ]
    return resposta(NS(content=None, tool_calls=calls))


class Cliente:
    def __init__(self, contato):
        self.respostas = [
            chamada(contato),
            resposta(NS(content="Ok", tool_calls=None)),
        ]
        self.chat = NS(completions=NS(create=lambda **_: self.respostas.pop(0)))


@pytest.mark.parametrize(
    "contato", ["anacarol.ferreira@coldmail.com", "(67) 99654-7821"]
)
def test_debug_nao_registra_contato(repo, caplog, contato):
    agente = Agent(
        cliente=Cliente(contato),
        config=Config(modelo="m", data_referencia=date(2026, 2, 20)),
        registro=REGISTRO,
        repo=repo,
        relogio=lambda: datetime(2026, 2, 20, 10, 0),
    )

    with caplog.at_level("DEBUG", logger="emporio"):
        agente.responder(SessionState(), f"pedido 8, {contato}")

    assert "consultar_pedido" in caplog.text
    assert contato not in caplog.text
    assert "BRJL5544332BR" not in caplog.text


def test_turno_anota_consultas_com_contato_mascarado(repo):
    contato = "anacarol.ferreira@coldmail.com"
    agente = Agent(
        cliente=Cliente(contato),
        config=Config(modelo="m", data_referencia=date(2026, 2, 20)),
        registro=REGISTRO,
        repo=repo,
        relogio=lambda: datetime(2026, 2, 20, 10, 0),
    )
    sessao = SessionState()

    agente.responder(sessao, f"pedido 8, {contato}")

    assert len(sessao.consultas_turno) == 1
    consulta = sessao.consultas_turno[0]
    assert consulta["nome"] == "consultar_pedido"
    assert consulta["duracao_ms"] >= 0
    assert json.loads(consulta["parametros"]) == {"numero_pedido": 8, "contato": "***"}


def test_consultas_nao_passam_de_um_turno_para_o_outro():
    cliente = NS(
        chat=NS(
            completions=NS(
                create=lambda **_: resposta(NS(content="Oi", tool_calls=None))
            )
        )
    )
    agente = Agent(
        cliente=cliente,
        config=Config(modelo="m", data_referencia=date(2026, 2, 20)),
        registro=REGISTRO,
        repo=None,
        relogio=lambda: datetime(2026, 2, 20, 10, 0),
    )
    sessao = SessionState()
    sessao.consultas_turno.append({"nome": "antiga"})

    agente.responder(sessao, "oi")

    assert sessao.consultas_turno == []


@pytest.mark.parametrize(
    "texto",
    [
        "Cliente ana@coldmail.com reclamou",
        "Ligar para (67) 99654-7821 amanhã",
        "Telefone 67996547821",
        "Número +55 67 99654-7821",
    ],
)
def test_mascara_contato_em_texto_livre(texto):
    saida = mascarar_argumentos(json.dumps({"resumo": texto}))

    assert "coldmail" not in saida
    assert "7821" not in saida
    assert "***" in saida


def test_mascara_alcanca_valores_aninhados():
    saida = mascarar_argumentos(json.dumps({"x": [{"contato": "a"}, "b@c.com"]}))
    assert json.loads(saida) == {"x": [{"contato": "***"}, "***"]}


def test_mascara_preserva_o_que_nao_e_contato():
    argumentos = {"texto": "Yamaha C40", "preco_max": 1000, "numero_pedido": 8}
    assert json.loads(mascarar_argumentos(json.dumps(argumentos))) == argumentos


@pytest.mark.parametrize("invalido", ["{quebrado", "[1]"])
def test_argumentos_invalidos_nao_aparecem(invalido):
    assert mascarar_argumentos(invalido) == "<argumentos inválidos>"
