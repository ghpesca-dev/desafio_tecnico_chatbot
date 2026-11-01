"""Inicialização da CLI, sem chamadas ao LLM."""

from emporio import cli


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
