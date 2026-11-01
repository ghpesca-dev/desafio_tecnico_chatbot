"""Regras de negócio puras: sem E/S, sem LLM e com dinheiro em Decimal."""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from unidecode import unidecode

CENTAVO = Decimal("0.01")
DESCONTO_PIX = Decimal("5")


def arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def formatar_brl(valor: Decimal) -> str:
    inteiro, centavos = f"{arredondar(valor):,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento e sem pontuação: `GD-20` vira `gd20`."""
    sem_acento = unidecode(texto).lower()
    sem_pontuacao = re.sub(r"[^a-z0-9\s]", "", sem_acento)
    return " ".join(sem_pontuacao.split())


def preco_atual(preco: Decimal, desconto_percentual: Decimal | None) -> Decimal:
    """Preço de tabela, ou promocional quando há promoção ativa."""
    if desconto_percentual is None:
        return arredondar(preco)
    return arredondar(preco * (100 - desconto_percentual) / 100)


@dataclass(frozen=True)
class Pix:
    valor: Decimal
    nao_acumula: bool


def calcular_pix(preco: Decimal, desconto_percentual: Decimal | None) -> Pix:
    """5% sobre a tabela; não se aplica sobre preço promocional (manual, 6.2)."""
    if desconto_percentual is not None:
        return Pix(preco_atual(preco, desconto_percentual), nao_acumula=True)
    return Pix(preco_atual(preco, DESCONTO_PIX), nao_acumula=False)


def situacao_produto(status: str, estoque: int, preco: Decimal | None) -> str:
    """`status` prevalece sobre o estoque."""
    if preco is None:
        return "sem_informacao"
    if status == "discontinued":
        return "fora_de_catalogo"
    if status == "coming_soon":
        return "em_breve"
    if status == "active":
        return "disponivel" if estoque > 0 else "temporariamente_indisponivel"
    return "sem_informacao"
