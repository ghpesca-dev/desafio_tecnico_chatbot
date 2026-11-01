"""Inicialização da CLI, sem chamadas ao LLM."""

from datetime import datetime

from emporio import cli
from emporio.complaints import Reclamacoes


def test_sem_chave_sai_com_erro(monkeypatch, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setattr("emporio.config.load_dotenv", lambda *_: None)

    assert cli.main([]) == 1
    assert "OPENROUTER_API_KEY" in capsys.readouterr().err


def test_data_invalida_sai_com_erro(monkeypatch, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    monkeypatch.setattr("emporio.config.load_dotenv", lambda *_: None)

    assert cli.main(["--data", "20-02-2026"]) == 1
    assert "AAAA-MM-DD" in capsys.readouterr().err


def test_sair_encerra_com_sucesso(monkeypatch, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    monkeypatch.setattr("emporio.config.load_dotenv", lambda *_: None)
    monkeypatch.setattr("builtins.input", lambda *_: "sair")

    assert cli.main(["--data", "2026-02-20"]) == 0
    assert "Pedido 3" not in capsys.readouterr().err


def test_reclamacoes_sem_registros_nao_exige_chave(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setattr("emporio.config.load_dotenv", lambda *_: None)
    monkeypatch.setattr(cli, "ARQUIVO_RECLAMACOES", tmp_path / "r.jsonl")

    assert cli.main(["reclamacoes"]) == 0
    assert "Nenhuma reclamação" in capsys.readouterr().out


def test_reclamacoes_lista_data_resumo_e_contato(monkeypatch, capsys, tmp_path):
    arquivo = tmp_path / "r.jsonl"
    monkeypatch.setattr(cli, "ARQUIVO_RECLAMACOES", arquivo)
    Reclamacoes(arquivo).registrar(
        sessao_id="s",
        resumo="Demorou demais",
        contato="maria@teste.com",
        momento=datetime(2026, 2, 20, 10, 0),
    )

    assert cli.main(["reclamacoes"]) == 0
    saida = capsys.readouterr().out
    assert "20/02/2026" in saida
    assert "Demorou demais" in saida
    assert "maria@teste.com" in saida
