"""Regras de negócio puras: sem E/S, sem LLM e com dinheiro em Decimal."""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from unidecode import unidecode

CENTAVO = Decimal("0.01")
DESCONTO_PIX = Decimal("5")
MINIMO_DIGITOS_TELEFONE = 8
DIAS_ARREPENDIMENTO = 7
DIAS_TROCA_PREFERENCIA = 7
DIAS_DEFEITO = 30
DIAS_GARANTIA_LEGAL = 90
BASE_ENTREGA = "previsao_entrega"
BASE_COMPRA = "data_compra"
STATUS_NAO_ENTREGUE = frozenset({"pending", "confirmed", "shipped"})


def arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def formatar_brl(valor: Decimal) -> str:
    inteiro, centavos = f"{arredondar(valor):,.2f}".split(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def formatar_percentual(valor: Decimal) -> str:
    return f"{valor.normalize():f}%"


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


def digitos_telefone(texto: str) -> str:
    """Só os dígitos, sem o código do país: `+55 67 99999-0000` vira `67999990000`."""
    digitos = re.sub(r"\D", "", texto)
    return digitos[2:] if len(digitos) >= 12 and digitos.startswith("55") else digitos


def contato_confere(informado: str, email: str, telefone: str) -> bool:
    """Compara com o cadastro: e-mail inteiro, ou telefone com ou sem DDD."""
    informado = informado.strip().lower()
    if not informado:
        return False
    if "@" in informado:
        return informado == email.strip().lower()
    digitos = digitos_telefone(informado)
    return len(digitos) >= MINIMO_DIGITOS_TELEFONE and digitos_telefone(
        telefone
    ).endswith(digitos)


@dataclass(frozen=True)
class Prazo:
    situacao: str
    ate: date | None
    base: str


def _prazo(inicio: date | None, dias: int, base: str, hoje: date) -> Prazo:
    if inicio is None:
        return Prazo("indeterminado", None, base)
    ate = inicio + timedelta(days=dias)
    # O último dia ainda está dentro do prazo.
    return Prazo("no_prazo" if hoje <= ate else "encerrado", ate, base)


def calcular_prazos(
    status: str, data_compra: date | None, previsao_entrega: date | None, hoje: date
) -> dict[str, Prazo]:
    """Prazos do manual, seção 4. A previsão de entrega aproxima o recebimento."""
    regras = {
        "arrependimento": (previsao_entrega, DIAS_ARREPENDIMENTO, BASE_ENTREGA),
        "troca_preferencia": (previsao_entrega, DIAS_TROCA_PREFERENCIA, BASE_ENTREGA),
        "defeito": (data_compra, DIAS_DEFEITO, BASE_COMPRA),
        "garantia_legal": (previsao_entrega, DIAS_GARANTIA_LEGAL, BASE_ENTREGA),
    }
    if status == "delivered":
        return {
            nome: _prazo(inicio, dias, base, hoje)
            for nome, (inicio, dias, base) in regras.items()
        }
    if status in STATUS_NAO_ENTREGUE:
        situacao = "nao_iniciado"
    elif status == "cancelled":
        situacao = "nao_se_aplica"
    else:
        situacao = "indeterminado"
    return {
        nome: Prazo(situacao, None, base)
        for nome, (_, _, base) in regras.items()
    }
