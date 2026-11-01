"""Consultas aos dados. Nenhum método público devolve e-mail, telefone ou id de cliente."""

from dataclasses import dataclass
from decimal import Decimal

from rapidfuzz import fuzz

from emporio.data.loader import Dados
from emporio.rules import normalizar, preco_atual, situacao_produto

MAX_RESULTADOS_BUSCA = 10
CORTE_CATEGORIA = 85
CORTE_TEXTO = 85
TAMANHO_MINIMO_APROXIMADO = 4
PALAVRAS_IGNORADAS = frozenset(
    "a as ao de do da dos das e em o os para instrumento outro todo".split()
)


def _radical(palavra: str) -> str:
    """Reduz plurais comuns: `violoes` e `violao` viram `violao`."""
    for sufixo, troca in (("oes", "ao"), ("aes", "ao")):
        if palavra.endswith(sufixo):
            return palavra[: -len(sufixo)] + troca
    return palavra[:-1] if palavra.endswith("s") and len(palavra) > 3 else palavra


def _palavras(texto: str) -> set[str]:
    radicais = {_radical(p) for p in normalizar(texto).split()}
    return radicais - PALAVRAS_IGNORADAS


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


@dataclass(frozen=True)
class ResultadoBusca:
    total: int
    produtos: list[Produto]
    categorias: list[Categoria]
    categoria_sem_itens: bool


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

    def resolver_categoria(self, texto: str) -> list[Categoria]:
        """Nome primeiro, depois descrição, depois nome aproximado."""
        palavras = _palavras(texto)
        por_nome = [
            c for c in self.categorias() if palavras & _palavras(c.nome)
        ]
        if por_nome:
            return por_nome
        por_descricao = [
            c for c in self.categorias() if palavras & _palavras(c.descricao)
        ]
        if por_descricao:
            return por_descricao
        return [
            c
            for c in self.categorias()
            if any(
                fuzz.ratio(p, q) >= CORTE_CATEGORIA
                for p in palavras
                for q in _palavras(c.nome)
            )
        ]

    def buscar_produtos(
        self,
        categoria: str | None = None,
        texto: str | None = None,
        preco_min: Decimal | None = None,
        preco_max: Decimal | None = None,
    ) -> ResultadoBusca:
        """Só produtos disponíveis, por menor preço atual."""
        candidatos = self.produtos()
        categorias: list[Categoria] = []
        sem_itens = False

        if categoria:
            categorias = self.resolver_categoria(categoria)
            ids = {c.id for c in categorias}
            candidatos = [p for p in candidatos if p.categoria_id in ids]
            sem_itens = bool(categorias) and not candidatos

        encontrados = [
            p
            for p in candidatos
            if p.situacao == "disponivel"
            and (preco_min is None or p.preco_atual >= preco_min)
            and (preco_max is None or p.preco_atual <= preco_max)
            and (not texto or self._coincide_texto(p, texto))
        ]
        encontrados.sort(key=lambda p: (p.preco_atual, p.id))

        return ResultadoBusca(
            total=len(encontrados),
            produtos=encontrados[:MAX_RESULTADOS_BUSCA],
            categorias=categorias,
            categoria_sem_itens=sem_itens,
        )

    @staticmethod
    def _coincide_texto(produto: Produto, texto: str) -> bool:
        """Toda palavra precisa aparecer no nome ou na categoria."""
        alvo = f"{produto.nome_normalizado} {normalizar(produto.categoria or '')}"
        alvo = f"{alvo} {' '.join(_palavras(alvo))}"
        for palavra in _palavras(texto):
            if palavra in alvo:
                continue
            if (
                len(palavra) < TAMANHO_MINIMO_APROXIMADO
                or fuzz.partial_ratio(palavra, alvo) < CORTE_TEXTO
            ):
                return False
        return True
