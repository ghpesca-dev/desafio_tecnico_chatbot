"""Cenários com LLM real. Pulam sem OPENROUTER_API_KEY e geram custo."""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pytest

from emporio.agent import Agent, criar_cliente
from emporio.complaints import Reclamacoes
from emporio.config import PASTA_POLITICAS, carregar_config
from emporio.policies import Politicas
from emporio.session import SessionState
from emporio.tools import REGISTRO

PASTA_E2E = Path(__file__).parent
VALOR_BRL = re.compile(r"R\$\s?\d[\d.]*(?:,\d{2})?")


def pytest_collection_modifyitems(config, items):
    tem_chave = bool(carregar_config().api_key)
    pular = pytest.mark.skip(reason="exige OPENROUTER_API_KEY")
    for item in items:
        if PASTA_E2E in Path(item.fspath).parents:
            item.add_marker(pytest.mark.e2e)
            if not tem_chave:
                item.add_marker(pular)


@dataclass
class Conversa:
    agente: Agent
    sessao: SessionState = field(default_factory=SessionState)

    def enviar(self, texto: str) -> str:
        resposta = self.agente.responder(self.sessao, texto)
        for termo in ("ferramenta", "tool_call", "sistema"):
            assert termo not in resposta.lower(), f"Termo interno: {termo}"
        return resposta

    @property
    def ferramentas(self) -> list[str]:
        return [
            chamada["function"]["name"]
            for mensagem in self.sessao.mensagens
            for chamada in mensagem.get("tool_calls") or []
        ]

    def resultados(self) -> list[dict]:
        return [
            json.loads(m["content"])
            for m in self.sessao.mensagens
            if m["role"] == "tool"
        ]

    def auditar_valores(self, resposta: str) -> None:
        """Todo valor em reais precisa ter vindo de ferramenta ou do cliente."""
        fontes = " ".join(
            m["content"]
            for m in self.sessao.mensagens
            if m["role"] in {"tool", "user"}
        )
        conhecidos = {_digitos(v) for v in VALOR_BRL.findall(fontes)}
        conhecidos |= {_digitos(n) for n in re.findall(r"\d[\d.,]*", fontes)}
        inventados = [
            v for v in VALOR_BRL.findall(resposta) if _digitos(v) not in conhecidos
        ]
        assert not inventados, f"Valores sem fonte: {inventados}"


def _digitos(valor: str) -> str:
    """Compara `R$ 1.000`, `R$ 1000` e `R$ 1.000,00` como o mesmo valor."""
    texto = re.sub(r"[^\d,]", "", valor)
    inteiro, _, centavos = texto.partition(",")
    return f"{int(inteiro or 0)},{(centavos or '00').ljust(2, '0')[:2]}"


def _nova_conversa(repositorio, arquivo, hora=10) -> Conversa:
    config = carregar_config("2026-02-20")
    agente = Agent(
        cliente=criar_cliente(config),
        config=config,
        registro=REGISTRO,
        repo=repositorio,
        relogio=lambda: datetime(2026, 2, 20, hora, 0),
        politicas=Politicas(PASTA_POLITICAS),
        reclamacoes=Reclamacoes(arquivo),
    )
    return Conversa(agente)


@pytest.fixture
def conversa(repo, tmp_path):
    return _nova_conversa(repo, tmp_path / "reclamacoes.jsonl")


@pytest.fixture
def conversa_incompleta(repo_fixture, tmp_path):
    """Pedido sem previsão de entrega, caso ausente nos dados reais."""
    return _nova_conversa(repo_fixture, tmp_path / "reclamacoes.jsonl")


@pytest.fixture
def conversa_noite(repo, tmp_path):
    """Sexta-feira às 20h, com a loja fechada."""
    return _nova_conversa(repo, tmp_path / "reclamacoes.jsonl", hora=20)
