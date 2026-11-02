"""Dashboard com LLM falso, sem rede."""

import json
import re
import threading
import time
import uuid
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

import emporio
from emporio.agent import FALLBACK, Agent
from emporio.api import criar_app
from emporio.config import Config
from emporio.historico import Historico
from emporio.tools import Registro

SEGREDO = "resultado-bruto-da-ferramenta"
PAGINA = Path(emporio.__file__).parent / "static" / "dashboard.html"


class ArgsPedido(BaseModel):
    numero_pedido: int
    contato: str


def criar_registro():
    registro = Registro()

    @registro.ferramenta("consultar_pedido", "Consulta pedido.", ArgsPedido)
    def consultar(args, contexto):
        return {"dado": SEGREDO}

    return registro


def texto(conteudo):
    return NS(choices=[NS(message=NS(content=conteudo, tool_calls=None))])


def chamada_de_pedido():
    calls = [
        NS(
            id="c0",
            type="function",
            function=NS(
                name="consultar_pedido",
                arguments=json.dumps({"numero_pedido": 8, "contato": "ana@x.com"}),
            ),
        )
    ]
    return NS(choices=[NS(message=NS(content=None, tool_calls=calls))])


class Cliente:
    def __init__(self):
        self.fila = []
        self.chat = NS(completions=NS(create=self._criar))

    def _criar(self, **_):
        return self.fila.pop(0) if self.fila else texto("Oi!")


def criar_agente(cliente, data=date(2026, 2, 20)):
    return Agent(
        cliente=cliente,
        config=Config(modelo="m", data_referencia=data, max_retries=0),
        registro=criar_registro(),
        repo=None,
        relogio=lambda: datetime(2026, 2, 20, 10, 0),
    )


@pytest.fixture
def cliente_llm():
    return Cliente()


@pytest.fixture
def historico(tmp_path):
    return Historico(tmp_path / "conversas")


@pytest.fixture
def api(cliente_llm, historico):
    with TestClient(criar_app(criar_agente(cliente_llm), historico)) as cliente:
        yield cliente


def enviar(api, mensagem="oi", session_id=None):
    corpo = {"mensagem": mensagem}
    if session_id:
        corpo["session_id"] = session_id
    return api.post("/chat", json=corpo)


# US1


def test_raiz_entrega_a_pagina(api):
    resposta = api.get("/")

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/html")
    assert "Empório da Música" in resposta.text


def test_chat_grava_a_troca(api, historico):
    corpo = enviar(api, "Tem violão?").json()

    conversa = historico.obter(corpo["session_id"])
    assert [m["texto"] for m in conversa["mensagens"]] == ["Tem violão?", "Oi!"]


def test_chat_mantem_o_contrato(api):
    assert set(enviar(api).json()) == {"session_id", "resposta"}


def test_falha_de_gravacao_nao_afeta_a_resposta(cliente_llm, tmp_path, caplog):
    arquivo = tmp_path / "ocupado"
    arquivo.write_text("x")
    agente = criar_agente(cliente_llm)

    with TestClient(criar_app(agente, Historico(arquivo))) as api:
        with caplog.at_level("WARNING", logger="emporio.api"):
            resposta = enviar(api)

    assert resposta.json()["resposta"] == "Oi!"
    assert "Falha ao gravar" in caplog.text


def test_contingencia_fica_no_historico(api, cliente_llm, historico):
    def falhar(**_):
        raise ValueError("sem resposta")

    cliente_llm.chat.completions.create = falhar

    corpo = enviar(api, "oi").json()

    assert corpo["resposta"] == FALLBACK
    mensagens = historico.obter(corpo["session_id"])["mensagens"]
    assert [m["texto"] for m in mensagens] == ["oi", FALLBACK]


def test_pagina_nao_interpreta_conteudo_como_html():
    fonte = PAGINA.read_text(encoding="utf-8")

    assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write", fonte)


def test_pagina_nao_depende_de_recursos_externos():
    fonte = PAGINA.read_text(encoding="utf-8")

    assert not re.search(r"https?://", fonte)
    assert not re.search(r"<script[^>]+src|<link[^>]+href", fonte)


# US2


def test_lista_conversas_da_mais_recente_para_a_mais_antiga(api):
    primeira = enviar(api, "primeira").json()["session_id"]
    time.sleep(0.01)
    segunda = enviar(api, "segunda").json()["session_id"]

    conversas = api.get("/conversas").json()["conversas"]

    assert [c["id"] for c in conversas] == [segunda, primeira]
    assert conversas[0]["titulo"] == "segunda"
    assert conversas[0]["atualizada_em"]
    assert conversas[0]["somente_leitura"] is False


def test_abre_conversa_com_todas_as_mensagens(api):
    sessao = enviar(api, "um").json()["session_id"]
    enviar(api, "dois", sessao)

    conversa = api.get(f"/conversas/{sessao}").json()

    assert [m["texto"] for m in conversa["mensagens"]] == ["um", "Oi!", "dois", "Oi!"]
    assert conversa["somente_leitura"] is False


def test_historico_guarda_mais_que_a_janela_do_modelo(cliente_llm, historico):
    agente = Agent(
        cliente=cliente_llm,
        config=Config(modelo="m", janela_trocas=2),
        registro=Registro(),
        repo=None,
        relogio=lambda: datetime(2026, 2, 20, 10, 0),
    )
    with TestClient(criar_app(agente, historico)) as api:
        sessao = enviar(api, "0").json()["session_id"]
        for numero in range(1, 5):
            enviar(api, str(numero), sessao)

        assert len(api.get(f"/conversas/{sessao}").json()["mensagens"]) == 10


def test_conversas_nao_se_misturam(api):
    a = enviar(api, "conversa a").json()["session_id"]
    b = enviar(api, "conversa b").json()["session_id"]
    enviar(api, "continua a", a)

    textos = [m["texto"] for m in api.get(f"/conversas/{b}").json()["mensagens"]]
    assert textos == ["conversa b", "Oi!"]


def test_reinicio_deixa_conversa_somente_leitura(cliente_llm, historico):
    with TestClient(criar_app(criar_agente(cliente_llm), historico)) as api:
        sessao = enviar(api, "oi").json()["session_id"]

    with TestClient(criar_app(criar_agente(cliente_llm), historico)) as api:
        conversa = api.get(f"/conversas/{sessao}").json()
        listada = api.get("/conversas").json()["conversas"][0]
        tentativa = enviar(api, "continua", sessao)

    assert [m["texto"] for m in conversa["mensagens"]] == ["oi", "Oi!"]
    assert conversa["somente_leitura"] is True
    assert listada["somente_leitura"] is True
    assert tentativa.status_code == 404


def test_confirmacao_de_identidade_nao_volta_com_o_historico(cliente_llm, historico):
    agente = criar_agente(cliente_llm)
    with TestClient(criar_app(agente, historico)) as api:
        sessao = enviar(api, "oi").json()["session_id"]

    with TestClient(criar_app(agente, historico)) as api:
        assert enviar(api, "pedido 8", sessao).status_code == 404
        assert cliente_llm.fila == []


def test_apagar_conversa(cliente_llm, historico):
    with TestClient(criar_app(criar_agente(cliente_llm), historico)) as api:
        sessao = enviar(api, "oi").json()["session_id"]

        assert api.delete(f"/conversas/{sessao}").status_code == 204
        assert api.get(f"/conversas/{sessao}").status_code == 404
        assert enviar(api, "de novo", sessao).status_code == 404

    with TestClient(criar_app(criar_agente(cliente_llm), historico)) as api:
        assert api.get("/conversas").json()["conversas"] == []


def test_apagar_conversa_somente_leitura(cliente_llm, historico):
    with TestClient(criar_app(criar_agente(cliente_llm), historico)) as api:
        sessao = enviar(api, "oi").json()["session_id"]

    with TestClient(criar_app(criar_agente(cliente_llm), historico)) as api:
        assert api.delete(f"/conversas/{sessao}").status_code == 204


@pytest.mark.parametrize("metodo", ["get", "delete"])
@pytest.mark.parametrize("conversa_id", ["inventado", "..%2F..%2F.env", str(uuid.uuid4())])
def test_conversa_inexistente_retorna_404(api, metodo, conversa_id):
    assert getattr(api, metodo)(f"/conversas/{conversa_id}").status_code == 404


def test_apagar_durante_resposta_nao_ressuscita_a_conversa(
    cliente_llm, historico
):
    na_chamada = threading.Event()
    liberar = threading.Event()

    def criar(**_):
        na_chamada.set()
        liberar.wait(5)
        return texto("Oi!")

    with TestClient(criar_app(criar_agente(cliente_llm), historico)) as api:
        sessao = enviar(api, "oi").json()["session_id"]
        cliente_llm.chat.completions.create = criar
        resultados = {}

        em_andamento = threading.Thread(
            target=lambda: resultados.update(a=enviar(api, "a", sessao))
        )
        em_andamento.start()
        assert na_chamada.wait(5)
        na_fila = threading.Thread(
            target=lambda: resultados.update(b=enviar(api, "b", sessao))
        )
        na_fila.start()
        apagando = threading.Thread(
            target=lambda: resultados.update(d=api.delete(f"/conversas/{sessao}"))
        )
        time.sleep(0.1)
        apagando.start()
        time.sleep(0.1)
        liberar.set()
        for fio in (em_andamento, na_fila, apagando):
            fio.join()

        assert resultados["a"].status_code == 200
        assert resultados["d"].status_code == 204
        assert api.get(f"/conversas/{sessao}").status_code == 404


# US3


def test_resposta_mostra_consultas_sem_contato_nem_resultado(
    api, cliente_llm, historico
):
    cliente_llm.fila = [chamada_de_pedido(), texto("Pedido a caminho.")]

    sessao = enviar(api, "pedido 8, ana@x.com").json()["session_id"]
    bruto = api.get(f"/conversas/{sessao}")
    agente = bruto.json()["mensagens"][1]

    assert agente["tempo_ms"] >= 0
    assert len(agente["consultas"]) == 1
    consulta = agente["consultas"][0]
    assert consulta["nome"] == "consultar_pedido"
    assert json.loads(consulta["parametros"]) == {"numero_pedido": 8, "contato": "***"}
    assert "duracao_ms" in consulta
    assert SEGREDO not in bruto.text
    assert SEGREDO not in historico._caminho(sessao).read_text(encoding="utf-8")


def test_resposta_sem_consulta_registra_lista_vazia(api):
    sessao = enviar(api).json()["session_id"]

    assert api.get(f"/conversas/{sessao}").json()["mensagens"][1]["consultas"] == []


def test_consultas_antigas_continuam_visiveis_depois_do_reinicio(
    cliente_llm, historico
):
    cliente_llm.fila = [chamada_de_pedido(), texto("Ok")]
    with TestClient(criar_app(criar_agente(cliente_llm), historico)) as api:
        sessao = enviar(api).json()["session_id"]

    with TestClient(criar_app(criar_agente(cliente_llm), historico)) as api:
        agente = api.get(f"/conversas/{sessao}").json()["mensagens"][1]

    assert agente["consultas"][0]["nome"] == "consultar_pedido"


# US4


def test_painel_com_historico_vazio(api):
    assert api.get("/conversas").json() == {
        "data_referencia": "2026-02-20",
        "conversas": [],
        "indicadores": {
            "conversas": 0,
            "mensagens_cliente": 0,
            "tempo_medio_ms": 0,
            "consultas_mais_usadas": [],
        },
    }


def test_painel_sem_data_fixada(cliente_llm, historico):
    with TestClient(criar_app(criar_agente(cliente_llm, None), historico)) as api:
        assert api.get("/conversas").json()["data_referencia"] is None


def test_painel_conta_o_historico(api, cliente_llm):
    cliente_llm.fila = [chamada_de_pedido(), texto("Ok")]
    sessao = enviar(api, "um").json()["session_id"]
    enviar(api, "dois", sessao)

    indicadores = api.get("/conversas").json()["indicadores"]

    assert indicadores["conversas"] == 1
    assert indicadores["mensagens_cliente"] == 2
    assert indicadores["consultas_mais_usadas"] == [
        {"nome": "consultar_pedido", "total": 1}
    ]


def test_arquivo_danificado_nao_derruba_o_painel(api, historico):
    sessao = enviar(api).json()["session_id"]
    (historico.pasta / f"{uuid.uuid4()}.json").write_text("{quebrado", encoding="utf-8")

    conversas = api.get("/conversas").json()["conversas"]

    assert [c["id"] for c in conversas] == [sessao]


# US5


def test_pagina_traz_exemplos_sem_dados_de_cliente():
    fonte = PAGINA.read_text(encoding="utf-8")

    for exemplo in ("Takamine GD20", "promoção", "pedido 8", "devolver", "bolo"):
        assert exemplo in fonte
    assert "@" not in fonte.replace("@media", "")
