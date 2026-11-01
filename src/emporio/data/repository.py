"""Consultas aos dados. Nenhum método público devolve e-mail, telefone ou id de cliente."""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from rapidfuzz import fuzz, process

from emporio.data.loader import Dados
from emporio.rules import contato_confere, normalizar, preco_atual, situacao_produto

MAX_RESULTADOS_BUSCA = 10
CORTE_CATEGORIA = 85
CORTE_TEXTO = 85
TAMANHO_MINIMO_APROXIMADO = 4
CORTE_REFERENCIA = 80
# Acima de `pedal` x `pearl` (80) e abaixo de `takamene` x `takamine` (87,5).
CORTE_PALAVRA = 85
MARGEM_EMPATE = 5
MAX_CANDIDATOS = 5
MAX_ALTERNATIVAS = 3
STATUS_PEDIDO = {
    "pending": "pendente",
    "confirmed": "confirmado",
    "shipped": "enviado",
    "delivered": "entregue",
    "cancelled": "cancelado",
}
PAGAMENTO = {"pix": "PIX", "debit": "cartão de débito", "boleto": "boleto"}
PRODUTO_SEM_NOME = "Produto não identificado"
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


def _palavra_no_nome(palavra: str, nome: str) -> bool:
    """Códigos com número são exatos: `gd30` não é `gd20`."""
    if palavra in nome:
        return True
    if any(c.isdigit() for c in palavra):
        return False
    return any(fuzz.ratio(palavra, n) >= CORTE_PALAVRA for n in nome.split())


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


@dataclass(frozen=True)
class ResultadoReferencia:
    tipo: str  # encontrado, ambiguo ou nao_encontrado
    produto: Produto | None = None
    candidatos: tuple[Produto, ...] = ()


@dataclass(frozen=True)
class PromocaoEncontrada:
    nome: str
    ativa: bool


@dataclass(frozen=True)
class ItemPedido:
    nome: str
    quantidade: int


@dataclass(frozen=True)
class Pedido:
    numero: int
    primeiro_nome: str | None
    status: str
    status_codigo: str
    data_compra: date | None
    total: Decimal | None
    pagamento: str
    rastreio: str | None
    previsao_entrega: date | None
    motivo_cancelamento: str | None
    itens: tuple[ItemPedido, ...]


def _traduzir_pagamento(codigo: str) -> str:
    parcelado = re.fullmatch(r"credit_(\d+)x", codigo)
    if parcelado:
        return f"cartão de crédito em {parcelado.group(1)}x"
    return PAGAMENTO.get(codigo, codigo)


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
        self._clientes = {
            c.customer_id: c for c in dados.clientes.itertuples(index=False)
        }
        self._pedidos = {
            p.order_id: p for p in dados.pedidos.itertuples(index=False)
        }
        self._itens: dict[int, list] = {}
        for item in dados.itens.itertuples(index=False):
            self._itens.setdefault(item.order_id, []).append(item)

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
        em_promocao: bool = False,
        promocao: str | None = None,
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
            and (not em_promocao or p.promocao_ativa)
            and (
                promocao is None
                or (p.promocao_ativa and p.promocao_ativa.nome == promocao)
            )
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

    def promocao_por_nome(self, texto: str) -> PromocaoEncontrada | None:
        """O mesmo nome pode estar ativa em um produto e encerrada em outro."""
        alvo = normalizar(texto)
        linhas = [
            p
            for p in self._promocoes.itertuples(index=False)
            if normalizar(p.description) == alvo
        ]
        if not linhas:
            return None
        return PromocaoEncontrada(
            linhas[0].description, any(p.is_active for p in linhas)
        )

    def buscar_referencia(self, referencia: str) -> ResultadoReferencia:
        """Id, depois sequência exata normalizada, depois nome aproximado."""
        referencia = referencia.strip()
        if referencia.isdigit():
            produto = self.produto(int(referencia))
            if produto:
                return ResultadoReferencia("encontrado", produto)

        sem_categoria = self._remover_palavras_de_categoria(referencia)
        return (
            self._por_sequencia_exata(referencia)
            or self._por_palavras(referencia)
            or self._por_sequencia_exata(sem_categoria)
            or self._por_palavras(sem_categoria)
            or self._por_aproximacao(sem_categoria)
        )

    def _remover_palavras_de_categoria(self, referencia: str) -> str:
        """`ukulele ohana ck20` vira `ohana ck20`: o tipo não está no nome."""
        categorias = {p for c in self.categorias() for p in _palavras(c.nome)}
        return " ".join(
            p
            for p in normalizar(referencia).split()
            if _radical(p) not in categorias and p not in PALAVRAS_IGNORADAS
        )

    @staticmethod
    def _classificar(produtos: list[Produto]) -> ResultadoReferencia | None:
        if not produtos:
            return None
        if len(produtos) == 1:
            return ResultadoReferencia("encontrado", produtos[0])
        return ResultadoReferencia(
            "ambiguo", candidatos=tuple(produtos[:MAX_CANDIDATOS])
        )

    def _por_sequencia_exata(self, referencia: str) -> ResultadoReferencia | None:
        # Sem espaços: `gf 3d`, `gf-3d` e `gf3d` são a mesma sequência.
        alvo = normalizar(referencia).replace(" ", "")
        if not alvo:
            return None
        return self._classificar(
            [
                p
                for p in self.produtos()
                if alvo in p.nome_normalizado.replace(" ", "")
            ]
        )

    def _por_palavras(self, referencia: str) -> ResultadoReferencia | None:
        palavras = normalizar(referencia).split()
        if not palavras:
            return None
        return self._classificar(
            [
                p
                for p in self.produtos()
                if all(palavra in p.nome_normalizado for palavra in palavras)
            ]
        )

    def _por_aproximacao(self, referencia: str) -> ResultadoReferencia:
        """Só afirma o produto se toda palavra coincidir; senão, pede confirmação.

        Informar o preço de outro modelo é pior do que perguntar: `gibson sg`
        não pode virar a Les Paul, nem `takamine gd30` o GD20.
        """
        consulta = normalizar(referencia)
        if not consulta:
            return ResultadoReferencia("nao_encontrado")

        palavras = consulta.split()
        cobrem_tudo = [
            p
            for p in self.produtos()
            if all(_palavra_no_nome(w, p.nome_normalizado) for w in palavras)
        ]
        if cobrem_tudo:
            return self._classificar(cobrem_tudo)

        nomes = {p.id: p.nome_normalizado for p in self.produtos()}
        resultados = process.extract(
            consulta,
            nomes,
            scorer=fuzz.WRatio,
            score_cutoff=CORTE_REFERENCIA,
            limit=None,
        )
        if not resultados:
            return ResultadoReferencia("nao_encontrado")
        melhor = resultados[0][1]
        proximos = [
            self.produto(chave)
            for _, pontos, chave in resultados
            if pontos >= melhor - MARGEM_EMPATE
        ]
        return ResultadoReferencia(
            "ambiguo", candidatos=tuple(proximos[:MAX_CANDIDATOS])
        )

    def pedido_confere(self, numero: int, contato: str) -> bool:
        """Compara só com o dono do pedido: um e-mail se repete entre clientes."""
        pedido = self._pedidos.get(numero)
        cliente = self._clientes.get(pedido.customer_id) if pedido else None
        if cliente is None:
            return False
        return contato_confere(contato, cliente.email, cliente.phone)

    def dados_pedido(self, numero: int) -> Pedido | None:
        """Dados para o cliente já confirmado, sem e-mail, telefone ou id."""
        linha = self._pedidos.get(numero)
        if linha is None:
            return None
        cliente = self._clientes.get(linha.customer_id)
        nomes = cliente.name.split() if cliente else []
        cancelado = linha.status == "cancelled"
        return Pedido(
            numero=linha.order_id,
            primeiro_nome=nomes[0] if nomes else None,
            status=STATUS_PEDIDO.get(linha.status, linha.status),
            status_codigo=linha.status,
            data_compra=linha.order_date,
            total=linha.total_brl,
            pagamento=_traduzir_pagamento(linha.payment_method),
            rastreio=linha.tracking_code or None,
            previsao_entrega=linha.estimated_delivery,
            # `notes` pode guardar anotações internas: só o motivo sai daqui.
            motivo_cancelamento=(linha.notes or None) if cancelado else None,
            itens=tuple(
                self._item_pedido(i) for i in self._itens.get(numero, [])
            ),
        )

    def _item_pedido(self, item) -> ItemPedido:
        produto = self.produto(item.product_id)
        return ItemPedido(
            produto.nome if produto else PRODUTO_SEM_NOME, item.quantity
        )

    def alternativas(self, produto: Produto) -> list[Produto]:
        """Disponíveis da mesma categoria, do preço mais próximo ao mais distante."""
        candidatos = [
            p
            for p in self.produtos()
            if p.situacao == "disponivel"
            and p.categoria_id == produto.categoria_id
            and p.id != produto.id
        ]
        if produto.preco is None:
            return candidatos[:MAX_ALTERNATIVAS]
        candidatos.sort(
            key=lambda p: (abs(p.preco_atual - produto.preco_atual), p.id)
        )
        return candidatos[:MAX_ALTERNATIVAS]
