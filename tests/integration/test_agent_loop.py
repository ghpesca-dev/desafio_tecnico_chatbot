"""Laço de tool use com um cliente LLM falso, sem rede."""

import json
from datetime import date, datetime
from types import SimpleNamespace as NS

import httpx
import openai
import pytest
from pydantic import BaseModel

from emporio.agent import FALLBACK, Agent
from emporio.config import Config
from emporio.session import SessionState
from emporio.tools import Registro


class Eco(BaseModel):
    texto: str


def texto(conteudo):
    return NS(choices=[NS(message=NS(content=conteudo, tool_calls=None))])


def chamada(*pares):
    calls = [
        NS(
            id=f"c{i}",
            type="function",
            function=NS(name=nome, arguments=json.dumps(args)),
        )
        for i, (nome, args) in enumerate(pares)
    ]
    return NS(choices=[NS(message=NS(content=None, tool_calls=calls))])


class ClienteFalso:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.pedidos = []
        self.chat = NS(completions=NS(create=self._criar))

    def _criar(self, **kwargs):
        # Copia as mensagens: a lista original muda ao longo do turno.
        self.pedidos.append({**kwargs, "messages": list(kwargs["messages"])})
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


@pytest.fixture
def registro():
    r = Registro()

    @r.ferramenta("eco", "Devolve o texto.", Eco)
    def eco(args, ctx):
        return {"eco": args.texto}

    @r.ferramenta("quebra", "Sempre falha.", Eco)
    def quebra(args, ctx):
        raise RuntimeError("segredo interno")

    return r


def criar_agente(cliente, registro, **config):
    return Agent(
        cliente=cliente,
        config=Config(modelo="m", data_referencia=date(2026, 2, 20), **config),
        registro=registro,
        repo=None,
        relogio=lambda: datetime(2026, 2, 20, 10, 0),
    )


def erro_api():
    return openai.APIConnectionError(
        request=httpx.Request("POST", "http://teste"),
    )


def papeis(sessao):
    return [m["role"] for m in sessao.mensagens]


def test_resposta_direta_sem_ferramenta(registro):
    cliente = ClienteFalso([texto("Oi!")])
    sessao = SessionState()
    assert criar_agente(cliente, registro).responder(sessao, "oi") == "Oi!"
    assert papeis(sessao) == ["user", "assistant"]


def test_executa_ferramenta_e_devolve_resultado(registro):
    cliente = ClienteFalso([chamada(("eco", {"texto": "x"})), texto("Pronto")])
    sessao = SessionState()

    assert criar_agente(cliente, registro).responder(sessao, "oi") == "Pronto"

    assert papeis(sessao) == ["user", "assistant", "tool", "assistant"]
    resultado = sessao.mensagens[2]
    assert resultado["tool_call_id"] == "c0"
    assert json.loads(resultado["content"]) == {"eco": "x"}


def test_resolve_varias_chamadas_na_mesma_resposta(registro):
    cliente = ClienteFalso(
        [chamada(("eco", {"texto": "a"}), ("eco", {"texto": "b"})), texto("Ok")]
    )
    sessao = SessionState()

    criar_agente(cliente, registro).responder(sessao, "oi")

    assert papeis(sessao) == ["user", "assistant", "tool", "tool", "assistant"]
    assert [m["tool_call_id"] for m in sessao.mensagens[2:4]] == ["c0", "c1"]


def test_erro_de_ferramenta_vira_resultado_sem_vazar_detalhe(registro):
    cliente = ClienteFalso([chamada(("quebra", {"texto": "x"})), texto("Ok")])
    sessao = SessionState()

    criar_agente(cliente, registro).responder(sessao, "oi")

    conteudo = sessao.mensagens[2]["content"]
    assert "erro" in json.loads(conteudo)
    assert "segredo interno" not in conteudo


def test_argumento_invalido_vira_erro_para_o_modelo(registro):
    cliente = ClienteFalso([chamada(("eco", {"errado": 1})), texto("Ok")])
    sessao = SessionState()

    criar_agente(cliente, registro).responder(sessao, "oi")

    assert "erro" in json.loads(sessao.mensagens[2]["content"])


def test_ferramenta_desconhecida_vira_erro(registro):
    cliente = ClienteFalso([chamada(("nao_existe", {})), texto("Ok")])
    sessao = SessionState()

    criar_agente(cliente, registro).responder(sessao, "oi")

    assert "erro" in json.loads(sessao.mensagens[2]["content"])


def test_encerra_com_fallback_apos_6_iteracoes(registro):
    cliente = ClienteFalso([chamada(("eco", {"texto": "x"})) for _ in range(20)])
    sessao = SessionState()

    resposta = criar_agente(cliente, registro).responder(sessao, "oi")

    assert resposta == FALLBACK
    assert "(67) 3341-4444" in resposta
    assert len(cliente.pedidos) == 6
    assert papeis(sessao)[-1] == "assistant"


def test_falha_do_llm_desfaz_o_turno_sem_chamada_orfa(registro):
    cliente = ClienteFalso(
        [texto("Oi!"), chamada(("eco", {"texto": "x"})), erro_api(), texto("Voltei")]
    )
    sessao = SessionState()
    agente = criar_agente(cliente, registro)
    agente.responder(sessao, "primeira")
    estado = list(sessao.mensagens)

    resposta = agente.responder(sessao, "segunda")

    assert "(67) 3341-4444" in resposta
    assert sessao.mensagens == estado
    assert agente.responder(sessao, "terceira") == "Voltei"


def test_resposta_sem_choices_usa_fallback(registro):
    cliente = ClienteFalso([NS(choices=None)])
    sessao = SessionState()

    resposta = criar_agente(cliente, registro).responder(sessao, "oi")

    assert "(67) 3341-4444" in resposta
    assert sessao.mensagens == []


def test_resposta_vazia_usa_fallback(registro):
    cliente = ClienteFalso([texto("   ")])
    resposta = criar_agente(cliente, registro).responder(SessionState(), "oi")
    assert "(67) 3341-4444" in resposta


def test_janela_nao_separa_chamada_e_resultado(registro):
    respostas = []
    for _ in range(14):
        respostas += [chamada(("eco", {"texto": "x"})), texto("Ok")]
    cliente = ClienteFalso(respostas)
    sessao = SessionState()
    agente = criar_agente(cliente, registro)

    for i in range(14):
        agente.responder(sessao, f"mensagem {i}")

    enviadas = cliente.pedidos[-1]["messages"]
    assert enviadas[0]["role"] == "system"
    assert enviadas[1]["role"] == "user"
    usuarios = [m for m in enviadas if m["role"] == "user"]
    assert len(usuarios) == 10
    ids_chamados = {
        c["id"] for m in enviadas for c in m.get("tool_calls") or []
    }
    assert ids_chamados
    for m in enviadas:
        if m["role"] == "tool":
            assert m["tool_call_id"] in ids_chamados


def test_envia_require_parameters(registro):
    cliente = ClienteFalso([texto("Oi")])
    criar_agente(cliente, registro).responder(SessionState(), "oi")
    assert cliente.pedidos[0]["extra_body"] == {
        "provider": {"require_parameters": True}
    }


def test_temperatura_nao_e_enviada_por_padrao(registro):
    cliente = ClienteFalso([texto("Oi")])
    criar_agente(cliente, registro).responder(SessionState(), "oi")
    assert "temperature" not in cliente.pedidos[0]


def test_temperatura_e_enviada_se_configurada(registro):
    cliente = ClienteFalso([texto("Oi")])
    criar_agente(cliente, registro, temperatura=0.2).responder(
        SessionState(), "oi"
    )
    assert cliente.pedidos[0]["temperature"] == 0.2


def test_system_prompt_e_refeito_com_a_data_e_hora(registro):
    cliente = ClienteFalso([texto("Oi")])
    criar_agente(cliente, registro).responder(SessionState(), "oi")
    system = cliente.pedidos[0]["messages"][0]
    assert system["role"] == "system"
    assert "20/02/2026" in system["content"]


def test_envia_schemas_das_ferramentas(registro):
    cliente = ClienteFalso([texto("Oi")])
    criar_agente(cliente, registro).responder(SessionState(), "oi")
    nomes = {t["function"]["name"] for t in cliente.pedidos[0]["tools"]}
    assert nomes == {"eco", "quebra"}


def test_log_mascara_contato(registro, caplog):
    class Pedido(BaseModel):
        contato: str

    @registro.ferramenta("pedido", "Teste.", Pedido)
    def pedido(args, ctx):
        return {}

    cliente = ClienteFalso(
        [chamada(("pedido", {"contato": "maria@teste.com"})), texto("Ok")]
    )
    with caplog.at_level("DEBUG", logger="emporio"):
        criar_agente(cliente, registro).responder(SessionState(), "oi")

    assert "pedido" in caplog.text
    assert "maria@teste.com" not in caplog.text
