"""O auditor dos cenários e2e precisa funcionar sem LLM: uma falha silenciosa o inutilizaria."""

import importlib.util
from pathlib import Path

import pytest

from emporio.session import SessionState

CAMINHO = Path(__file__).resolve().parents[1] / "e2e" / "conftest.py"
espec = importlib.util.spec_from_file_location("e2e_conftest", CAMINHO)
modulo = importlib.util.module_from_spec(espec)
espec.loader.exec_module(modulo)


def conversa(*fontes):
    sessao = SessionState()
    for papel, texto in fontes:
        sessao.mensagens.append({"role": papel, "content": texto})
    return modulo.Conversa(agente=None, sessao=sessao)


def test_aceita_valor_vindo_de_ferramenta():
    c = conversa(("tool", '{"preco_atual": "R$ 2.199,00"}'))
    c.auditar_valores("Sai por R$ 2.199,00.")


def test_aceita_valor_citado_pelo_cliente_em_outro_formato():
    c = conversa(("user", "violões até R$ 1000?"))
    c.auditar_valores("Até R$ 1.000,00 tenho estas opções.")


def test_recusa_valor_inventado():
    c = conversa(("tool", '{"preco_atual": "R$ 2.199,00"}'))
    with pytest.raises(AssertionError, match="1.999"):
        c.auditar_valores("Sai por R$ 1.999,00.")


def test_ignora_o_texto_do_proprio_assistente():
    c = conversa(("assistant", "Custa R$ 50,00."))
    with pytest.raises(AssertionError):
        c.auditar_valores("Custa R$ 50,00.")
