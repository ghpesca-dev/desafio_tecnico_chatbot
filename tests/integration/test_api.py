"""API com LLM falso, sem rede."""

import threading
from datetime import date, datetime
from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

from emporio.agent import Agent
from emporio.api import criar_app
from emporio.config import Config
from emporio.historico import Historico
from emporio.tools import Registro


class Cliente:
    def __init__(self):
        self.mensagens = []
        self.chat = NS(completions=NS(create=self._criar))

    def _criar(self, **kwargs):
        self.mensagens.append(kwargs["messages"])
        mensagem = NS(content="Oi!", tool_calls=None)
        return NS(choices=[NS(message=mensagem)])


@pytest.fixture
def cliente_llm():
    return Cliente()


@pytest.fixture
def api(cliente_llm, tmp_path):
    agente = Agent(
        cliente=cliente_llm,
        config=Config(modelo="m", data_referencia=date(2026, 2, 20)),
        registro=Registro(),
        repo=None,
        relogio=lambda: datetime(2026, 2, 20, 10, 0),
    )
    with TestClient(criar_app(agente, Historico(tmp_path))) as cliente:
        yield cliente


def test_health(api):
    assert api.get("/health").json() == {"status": "ok"}


def test_sem_session_id_cria_sessao(api):
    resposta = api.post("/chat", json={"mensagem": "oi"})

    assert resposta.status_code == 200
    assert resposta.json()["resposta"] == "Oi!"
    assert resposta.json()["session_id"]


def test_duas_chamadas_sem_id_criam_sessoes_diferentes(api):
    primeira = api.post("/chat", json={"mensagem": "oi"}).json()
    segunda = api.post("/chat", json={"mensagem": "oi"}).json()
    assert primeira["session_id"] != segunda["session_id"]


def test_mesma_sessao_mantem_o_historico(api, cliente_llm):
    sessao = api.post("/chat", json={"mensagem": "primeira"}).json()["session_id"]
    api.post("/chat", json={"session_id": sessao, "mensagem": "segunda"})

    conteudos = [m["content"] for m in cliente_llm.mensagens[-1]]
    assert "primeira" in conteudos
    assert "segunda" in conteudos


def test_sessao_desconhecida_retorna_404(api):
    resposta = api.post("/chat", json={"session_id": "inventado", "mensagem": "oi"})
    assert resposta.status_code == 404


@pytest.mark.parametrize("corpo", [{"mensagem": ""}, {"mensagem": "   "}, {}])
def test_mensagem_vazia_retorna_422(api, corpo):
    assert api.post("/chat", json=corpo).status_code == 422


def test_resposta_nao_expoe_chamadas_de_ferramenta(api):
    corpo = api.post("/chat", json={"mensagem": "oi"}).json()
    assert set(corpo) == {"session_id", "resposta"}


def test_mesma_sessao_processa_uma_mensagem_por_vez(cliente_llm, tmp_path):
    em_andamento = []
    simultaneas = []
    liberar = threading.Event()

    def criar(**kwargs):
        em_andamento.append(1)
        simultaneas.append(len(em_andamento))
        liberar.wait(0.1)
        em_andamento.pop()
        mensagem = NS(content="Oi!", tool_calls=None)
        return NS(choices=[NS(message=mensagem)])

    cliente_llm.chat.completions.create = criar
    agente = Agent(
        cliente=cliente_llm,
        config=Config(modelo="m", data_referencia=date(2026, 2, 20)),
        registro=Registro(),
        repo=None,
        relogio=lambda: datetime(2026, 2, 20, 10, 0),
    )
    with TestClient(criar_app(agente, Historico(tmp_path))) as api:
        sessao = api.post("/chat", json={"mensagem": "oi"}).json()["session_id"]
        fios = [
            threading.Thread(
                target=api.post,
                args=("/chat",),
                kwargs={"json": {"session_id": sessao, "mensagem": "oi"}},
            )
            for _ in range(3)
        ]
        for fio in fios:
            fio.start()
        for fio in fios:
            fio.join()

    assert max(simultaneas) == 1
