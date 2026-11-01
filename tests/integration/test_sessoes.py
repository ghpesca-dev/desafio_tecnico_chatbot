"""Sessões simultâneas não dividem histórico nem confirmações."""

import json
from datetime import date, datetime
from types import SimpleNamespace as NS

from emporio.agent import Agent
from emporio.config import Config
from emporio.session import SessionState
from emporio.tools import REGISTRO, Contexto


def texto(conteudo):
    return NS(choices=[NS(message=NS(content=conteudo, tool_calls=None))])


class Cliente:
    def __init__(self):
        self.pedidos = []
        self.chat = NS(completions=NS(create=self._criar))

    def _criar(self, **kwargs):
        self.pedidos.append(list(kwargs["messages"]))
        return texto("Ok")


def criar_agente(cliente, repo=None):
    return Agent(
        cliente=cliente,
        config=Config(modelo="m", data_referencia=date(2026, 2, 20)),
        registro=REGISTRO,
        repo=repo,
        relogio=lambda: datetime(2026, 2, 20, 10, 0),
    )


def test_historico_nao_passa_de_uma_sessao_para_outra():
    cliente = Cliente()
    agente = criar_agente(cliente)
    primeira, segunda = SessionState(), SessionState()

    agente.responder(primeira, "segredo da primeira")
    agente.responder(segunda, "oi")

    conteudo = json.dumps(cliente.pedidos[-1], ensure_ascii=False)
    assert "segredo da primeira" not in conteudo
    assert len(primeira.mensagens) == len(segunda.mensagens) == 2


def test_ids_de_sessao_sao_diferentes():
    assert SessionState().id != SessionState().id


def test_confirmacao_nao_passa_para_outra_sessao(repo):
    primeira, segunda = SessionState(), SessionState()
    primeira.registrar_mensagem_cliente("anacarol.ferreira@coldmail.com")

    def consultar(sessao, **args):
        contexto = Contexto(repo, sessao, date(2026, 2, 20))
        return json.loads(
            REGISTRO.despachar("consultar_pedido", json.dumps(args), contexto)
        )["resultado"]

    assert (
        consultar(
            primeira, numero_pedido=8, contato="anacarol.ferreira@coldmail.com"
        )
        == "ok"
    )
    assert consultar(segunda, numero_pedido=8) == "precisa_confirmacao"


def test_falhas_nao_passam_para_outra_sessao(repo):
    primeira, segunda = SessionState(), SessionState()
    primeira.registrar_falha_confirmacao()
    primeira.registrar_falha_confirmacao()
    primeira.registrar_falha_confirmacao()

    assert primeira.bloqueada
    assert not segunda.bloqueada
