"""Fixtures compartilhadas: dados reais e CSVs mínimos para casos ausentes neles."""

from datetime import date
from pathlib import Path

import pytest

from emporio.data.loader import carregar_dados
from emporio.data.repository import Repository

RAIZ = Path(__file__).resolve().parents[1]
DATA_REFERENCIA = date(2026, 2, 20)


@pytest.fixture(scope="session")
def dados():
    return carregar_dados(RAIZ / "data")


@pytest.fixture(scope="session")
def repo(dados):
    return Repository(dados)


@pytest.fixture(scope="session")
def dados_fixture():
    return carregar_dados(RAIZ / "tests" / "fixtures")


@pytest.fixture(scope="session")
def repo_fixture(dados_fixture):
    return Repository(dados_fixture)
