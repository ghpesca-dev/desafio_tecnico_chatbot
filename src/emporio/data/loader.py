"""Leitura, validação e enriquecimento dos CSVs."""

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from emporio.rules import normalizar

logger = logging.getLogger("emporio.dados")

PREFIXO = "desafio_tecnico_ai_eng - "
TOTAL_PRODUTOS_ESPERADO = 65

COLUNAS = {
    "products": {
        "product_id", "price_brl", "name", "category_id", "description",
        "stock_quantity", "status", "specs",
    },
    "categories": {"category_id", "name", "description"},
    "promotions": {
        "promotion_id", "product_id", "discount_percent", "description",
        "is_active",
    },
    "orders": {
        "order_id", "customer_id", "order_date", "status", "total_brl",
        "payment_method", "tracking_code", "estimated_delivery", "notes",
    },
    "order_items": {"order_id", "quantity", "product_id"},
    "customers": {"customer_id", "name", "phone", "email"},
}


class DadosInvalidos(Exception):
    """Os arquivos não permitem iniciar o agente."""


@dataclass
class Dados:
    produtos: pd.DataFrame
    categorias: pd.DataFrame
    promocoes: pd.DataFrame
    pedidos: pd.DataFrame
    itens: pd.DataFrame
    clientes: pd.DataFrame
    avisos: list[str] = field(default_factory=list)


def _ler(pasta: Path, tabela: str) -> pd.DataFrame:
    caminho = pasta / f"{PREFIXO}{tabela}.csv"
    if not caminho.exists():
        raise DadosInvalidos(f"Arquivo não encontrado: {caminho}")
    # Tudo como texto: a conversão de dinheiro não pode passar por float.
    df = pd.read_csv(caminho, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    faltando = COLUNAS[tabela] - set(df.columns)
    if faltando:
        raise DadosInvalidos(
            f"Colunas faltando em {tabela}: {', '.join(sorted(faltando))}"
        )
    return df


def _decimal(texto: str) -> Decimal | None:
    try:
        return Decimal(texto) if texto.strip() else None
    except InvalidOperation:
        return None


def _inteiro(texto: str) -> int | None:
    try:
        return int(texto)
    except ValueError:
        return None


def _data(texto: str) -> date | None:
    try:
        return date.fromisoformat(texto) if texto.strip() else None
    except ValueError:
        return None


def _objetos(valores) -> pd.Series:
    """Série de objetos Python, preservando Decimal, date e None."""
    return pd.Series(list(valores), dtype=object)


def _preparar_produtos(
    df: pd.DataFrame, categorias: pd.DataFrame, avisos: list[str]
) -> pd.DataFrame:
    nomes_categoria = dict(zip(categorias["category_id"], categorias["name"]))
    df = df.reset_index(drop=True).copy()
    specs, nomes, incompletos, precos, estoques = [], [], [], [], []

    for linha in df.itertuples(index=False):
        rotulo = f"Produto {linha.product_id}"
        incompleto = False

        try:
            spec = json.loads(linha.specs) if linha.specs.strip() else {}
        except json.JSONDecodeError:
            avisos.append(f"{rotulo}: specs com JSON inválido; ignorado.")
            spec = {}

        preco = _decimal(linha.price_brl)
        if preco is None or preco <= 0:
            avisos.append(f"{rotulo}: sem preço válido.")
            preco = None
            incompleto = True

        estoque = _inteiro(linha.stock_quantity)
        if estoque is None or estoque < 0:
            avisos.append(f"{rotulo}: estoque inválido.")
            estoque = 0
            incompleto = True

        categoria = nomes_categoria.get(_inteiro(linha.category_id))
        if categoria is None:
            avisos.append(f"{rotulo}: categoria {linha.category_id} inexistente.")
            incompleto = True

        specs.append(spec)
        nomes.append(categoria)
        incompletos.append(incompleto)
        precos.append(preco)
        estoques.append(estoque)

    df["product_id"] = df["product_id"].astype(int)
    df["category_id"] = df["category_id"].map(_inteiro).astype(object)
    df["price_brl"] = _objetos(precos)
    df["stock_quantity"] = estoques
    df["specs"] = _objetos(specs)
    df["categoria"] = _objetos(nomes)
    df["dados_incompletos"] = incompletos
    df["nome_normalizado"] = df["name"].map(normalizar)
    return df


def _preparar_promocoes(
    df: pd.DataFrame, ids_produto: set[int], avisos: list[str]
) -> pd.DataFrame:
    df = df.reset_index(drop=True).copy()
    df["promotion_id"] = df["promotion_id"].astype(int)
    df["product_id"] = df["product_id"].astype(int)
    df["discount_percent"] = _objetos(map(_decimal, df["discount_percent"]))
    df["is_active"] = df["is_active"] == "1"

    validas = []
    for linha in df.itertuples(index=False):
        rotulo = f"Promoção {linha.promotion_id}"
        desconto = linha.discount_percent
        if linha.product_id not in ids_produto:
            avisos.append(f"{rotulo}: produto {linha.product_id} inexistente.")
            validas.append(False)
        elif desconto is None or not 0 < desconto < 100:
            avisos.append(f"{rotulo}: desconto inválido.")
            validas.append(False)
        else:
            validas.append(True)
    return df[validas].reset_index(drop=True)


def _preparar_pedidos(
    pedidos: pd.DataFrame,
    itens: pd.DataFrame,
    produtos: pd.DataFrame,
    clientes: pd.DataFrame,
    avisos: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    pedidos = pedidos.reset_index(drop=True).copy()
    pedidos["order_id"] = pedidos["order_id"].astype(int)
    pedidos["customer_id"] = pedidos["customer_id"].map(_inteiro).astype(object)
    pedidos["total_brl"] = _objetos(map(_decimal, pedidos["total_brl"]))
    pedidos["order_date"] = _objetos(map(_data, pedidos["order_date"]))
    pedidos["estimated_delivery"] = _objetos(
        map(_data, pedidos["estimated_delivery"])
    )

    itens = itens.reset_index(drop=True).copy()
    itens["order_id"] = itens["order_id"].astype(int)
    itens["product_id"] = itens["product_id"].astype(int)
    itens["quantity"] = itens["quantity"].astype(int)

    precos = dict(zip(produtos["product_id"], produtos["price_brl"]))
    ids_cliente = set(clientes["customer_id"])

    for linha in pedidos.itertuples(index=False):
        rotulo = f"Pedido {linha.order_id}"
        if linha.customer_id not in ids_cliente:
            avisos.append(f"{rotulo}: cliente {linha.customer_id} inexistente.")

        do_pedido = itens[itens["order_id"] == linha.order_id]
        valores = [
            (precos.get(i.product_id), i.quantity)
            for i in do_pedido.itertuples(index=False)
        ]
        if not valores or any(preco is None for preco, _ in valores):
            avisos.append(f"{rotulo}: itens ausentes ou com produto sem preço.")
            continue
        soma = sum(preco * quantidade for preco, quantidade in valores)
        if linha.total_brl != soma:
            avisos.append(
                f"{rotulo}: total {linha.total_brl} difere da soma "
                f"pelo preço atual ({soma}); vale o total registrado."
            )
    return pedidos, itens


def carregar_dados(pasta: Path) -> Dados:
    """Carrega os seis CSVs e aplica a validação da inicialização."""
    pasta = Path(pasta)
    avisos: list[str] = []

    categorias = _ler(pasta, "categories")
    categorias["category_id"] = categorias["category_id"].astype(int)

    clientes = _ler(pasta, "customers")
    clientes["customer_id"] = clientes["customer_id"].astype(int)

    produtos = _preparar_produtos(_ler(pasta, "products"), categorias, avisos)
    if len(produtos) != TOTAL_PRODUTOS_ESPERADO:
        avisos.append(
            f"Catálogo com {len(produtos)} produtos; o esperado é "
            f"{TOTAL_PRODUTOS_ESPERADO}."
        )

    promocoes = _preparar_promocoes(
        _ler(pasta, "promotions"), set(produtos["product_id"]), avisos
    )
    pedidos, itens = _preparar_pedidos(
        _ler(pasta, "orders"), _ler(pasta, "order_items"), produtos, clientes, avisos
    )

    for aviso in avisos:
        logger.warning(aviso)

    return Dados(produtos, categorias, promocoes, pedidos, itens, clientes, avisos)
