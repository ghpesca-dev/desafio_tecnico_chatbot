"""Variáveis de ambiente e parâmetros do agente."""

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
PASTA_DADOS = RAIZ / "data"
PASTA_POLITICAS = PASTA_DADOS / "processed" / "politicas"
ARQUIVO_RECLAMACOES = PASTA_DADOS / "runtime" / "reclamacoes.jsonl"

BASE_URL = "https://openrouter.ai/api/v1"
MODELO_PADRAO = "anthropic/claude-haiku-5.5"
FUSO = ZoneInfo("America/Campo_Grande")


class ConfiguracaoInvalida(Exception):
    """Valor de configuração que impede a inicialização."""


@dataclass(frozen=True)
class Config:
    modelo: str = MODELO_PADRAO
    api_key: str | None = None
    temperatura: float | None = None
    data_referencia: date | None = None
    max_iteracoes: int = 6
    janela_trocas: int = 10
    timeout_s: float = 30.0
    max_retries: int = 2
    limite_chamada_s: float = 60.0


def _ler_data(texto: str, origem: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError as erro:
        raise ConfiguracaoInvalida(
            f"{origem} deve estar no formato AAAA-MM-DD: {texto!r}"
        ) from erro


def _ler_temperatura(texto: str) -> float:
    try:
        return float(texto)
    except ValueError as erro:
        raise ConfiguracaoInvalida(
            f"OPENROUTER_TEMPERATURE deve ser um número: {texto!r}"
        ) from erro


def carregar_config(data_cli: str | None = None) -> Config:
    """Lê o ambiente. `--data` tem prioridade sobre `EMPORIO_DATA_REFERENCIA`."""
    load_dotenv(RAIZ / ".env")

    data_env = os.getenv("EMPORIO_DATA_REFERENCIA", "").strip()
    data_referencia = None
    if data_cli:
        data_referencia = _ler_data(data_cli, "--data")
    elif data_env:
        data_referencia = _ler_data(data_env, "EMPORIO_DATA_REFERENCIA")

    temperatura = os.getenv("OPENROUTER_TEMPERATURE", "").strip()

    return Config(
        modelo=os.getenv("OPENROUTER_MODEL", "").strip() or MODELO_PADRAO,
        api_key=os.getenv("OPENROUTER_API_KEY", "").strip() or None,
        temperatura=_ler_temperatura(temperatura) if temperatura else None,
        data_referencia=data_referencia,
    )


def criar_relogio(data_fixa: date | None) -> Callable[[], datetime]:
    """Relógio em Campo Grande; com data fixa, só a hora continua real."""

    def agora() -> datetime:
        atual = datetime.now(FUSO)
        if data_fixa is None:
            return atual
        return datetime.combine(data_fixa, atual.timetz())

    return agora
