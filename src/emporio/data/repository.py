"""Consultas aos dados. Nenhum método público devolve e-mail, telefone ou id de cliente."""

from dataclasses import dataclass
from decimal import Decimal

from emporio.data.loader import Dados
from emporio.rules import preco_atual, situacao_produto


@dataclass(frozen=True)
class Promocao:
    id: int
    nome: str
    desconto: Decimal


@dataclass(frozen=True)
class Categoria:
    id: int
    nome: str
    descricao: str


@dataclass(frozen=True)
class Produto:
    id: int
    nome: str
    nome_normalizado: str
    categoria_id: int | None
    categoria: str | None
    descricao: str
    preco: Decimal | None
    situacao: str
    specs: dict
    promocao_ativa: Promocao | None
    promocao_encerrada: Promocao | None

    @property
    def preco_atual(self) -> Decimal | None:
        if self.preco is None:
            return None
        desconto = self.promocao_ativa.desconto if self.promocao_ativa else None
        return preco_atual(self.preco, desconto)


class Repository:
    def __init__(self, dados: Dados):
        self._categorias = {
            c.category_id: Categoria(c.category_id, c.name, c.description)
            for c in dados.categorias.itertuples(index=False)
        }
        self._promocoes = dados.promocoes
        self._produtos = {
            p.product_id: self._montar_produto(p)
            for p in dados.produtos.itertuples(index=False)
        }

    def _promocao_ativa(self, produto_id: int) -> Promocao | None:
        linhas = self._promocoes[
            (self._promocoes["product_id"] == produto_id)
            & self._promocoes["is_active"]
        ]
        if linhas.empty:
            return None
        return self._promocao(max(
            linhas.itertuples(index=False), key=lambda p: p.discount_percent
        ))

    def _promocao_encerrada(self, produto_id: int) -> Promocao | None:
        linhas = self._promocoes[
            (self._promocoes["product_id"] == produto_id)
            & ~self._promocoes["is_active"]
        ]
        if linhas.empty:
            return None
        return self._promocao(max(
            linhas.itertuples(index=False), key=lambda p: p.promotion_id
        ))

    @staticmethod
    def _promocao(linha) -> Promocao:
        return Promocao(linha.promotion_id, linha.description, linha.discount_percent)

    def _montar_produto(self, linha) -> Produto:
        ativa = self._promocao_ativa(linha.product_id)
        incompleto = linha.dados_incompletos
        return Produto(
            id=linha.product_id,
            nome=linha.name,
            nome_normalizado=linha.nome_normalizado,
            categoria_id=linha.category_id,
            categoria=linha.categoria,
            descricao=linha.description,
            preco=linha.price_brl,
            situacao=(
                "sem_informacao"
                if incompleto
                else situacao_produto(
                    linha.status, linha.stock_quantity, linha.price_brl
                )
            ),
            specs=linha.specs,
            promocao_ativa=ativa,
            # Promoção encerrada só importa quando não há outra ativa.
            promocao_encerrada=(
                None if ativa else self._promocao_encerrada(linha.product_id)
            ),
        )

    def produto(self, produto_id: int) -> Produto | None:
        return self._produtos.get(produto_id)

    def produtos(self) -> list[Produto]:
        return list(self._produtos.values())

    def categorias(self) -> list[Categoria]:
        return list(self._categorias.values())
