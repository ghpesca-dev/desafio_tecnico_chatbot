"""O log de depuração não pode guardar dados de contato."""

from datetime import date, datetime
from types import SimpleNamespace as NS
import json

import pytest

from emporio.agent import Agent
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
