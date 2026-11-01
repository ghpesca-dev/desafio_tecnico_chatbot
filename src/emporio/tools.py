"""Ferramentas expostas ao LLM: schemas, despacho e implementações."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints, ValidationError

from emporio.data.repository import Produto, Repository
from emporio.policies import Politicas, Topico
from emporio.rules import calcular_pix, formatar_brl, formatar_percentual
from emporio.session import SessionState

logger = logging.getLogger("emporio.ferramentas")


@dataclass
class Contexto:
    """Dependências de uma execução; o modelo nunca as controla."""

    repo: Repository | None
    sessao: SessionState
    data_referencia: date
    politicas: Politicas | None = None


@dataclass(frozen=True)
class Ferramenta:
    nome: str
    descricao: str
    modelo_args: type[BaseModel]
    executar: Callable[[BaseModel, Contexto], Any]


class Registro:
    def __init__(self) -> None:
        self._ferramentas: dict[str, Ferramenta] = {}

    def ferramenta(self, nome: str, descricao: str, modelo_args: type[BaseModel]):
        def decorador(funcao):
            self._ferramentas[nome] = Ferramenta(
                nome, descricao, modelo_args, funcao
            )
            return funcao

        return decorador

    def schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": f.nome,
                    "description": f.descricao,
                    "parameters": f.modelo_args.model_json_schema(),
                },
            }
            for f in self._ferramentas.values()
        ]

    def despachar(self, nome: str, argumentos: str, contexto: Contexto) -> str:
        """Executa e devolve JSON; erros voltam ao modelo em vez de encerrar o turno."""
        return json.dumps(
            self._executar(nome, argumentos, contexto), ensure_ascii=False
        )

    def _executar(self, nome: str, argumentos: str, contexto: Contexto) -> dict:
        ferramenta = self._ferramentas.get(nome)
        if ferramenta is None:
            return {"erro": f"Ferramenta desconhecida: {nome}"}
        try:
            args = ferramenta.modelo_args.model_validate_json(argumentos or "{}")
        except ValidationError as erro:
            campos = ", ".join(str(e["loc"][-1]) for e in erro.errors() if e["loc"])
            return {"erro": f"Argumentos inválidos: {campos or 'formato'}"}
        try:
            resultado = ferramenta.executar(args, contexto)
        except Exception:
            # O detalhe fica no log: não deve chegar ao modelo nem ao cliente.
            logger.exception("Falha na ferramenta %s", nome)
            return {"erro": "Não foi possível consultar essa informação agora."}
        if isinstance(resultado, BaseModel):
            return resultado.model_dump(mode="json")
        return resultado


REGISTRO = Registro()


class ProdutoResumo(BaseModel):
    id: int
    nome: str
    categoria: str
    preco_atual: str
    preco_original: str | None
    desconto_percentual: str | None
    promocao: str | None
    disponivel: bool


def resumir_produto(produto: Produto) -> ProdutoResumo:
    promocao = produto.promocao_ativa
    return ProdutoResumo(
        id=produto.id,
        nome=produto.nome,
        categoria=produto.categoria,
        preco_atual=formatar_brl(produto.preco_atual),
        preco_original=formatar_brl(produto.preco) if promocao else None,
        desconto_percentual=(
            formatar_percentual(promocao.desconto) if promocao else None
        ),
        promocao=promocao.nome if promocao else None,
        disponivel=produto.situacao == "disponivel",
    )


class ArgsBuscarProdutos(BaseModel):
    categoria: str | None = Field(
        None, description="Tipo de instrumento, como violão, guitarra ou teclado."
    )
    texto: str | None = Field(None, description="Nome ou marca do produto.")
    preco_min: Decimal | None = Field(None, description="Preço mínimo, em reais.")
    preco_max: Decimal | None = Field(None, description="Preço máximo, em reais.")


class SaidaBuscarProdutos(BaseModel):
    total_encontrado: int
    exibidos: int
    categoria_resolvida: str | None
    categoria_sem_itens: bool
    produtos: list[ProdutoResumo]


@REGISTRO.ferramenta(
    "buscar_produtos",
    "Lista produtos disponíveis por tipo, nome ou marca e faixa de preço.",
    ArgsBuscarProdutos,
)
def buscar_produtos(args: ArgsBuscarProdutos, ctx: Contexto) -> SaidaBuscarProdutos:
    resultado = ctx.repo.buscar_produtos(
        categoria=args.categoria,
        texto=args.texto,
        preco_min=args.preco_min,
        preco_max=args.preco_max,
    )
    return SaidaBuscarProdutos(
        total_encontrado=resultado.total,
        exibidos=len(resultado.produtos),
        categoria_resolvida=", ".join(c.nome for c in resultado.categorias) or None,
        categoria_sem_itens=resultado.categoria_sem_itens,
        produtos=[resumir_produto(p) for p in resultado.produtos],
    )


class ArgsDetalhesProduto(BaseModel):
    referencia: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(description="Nome do produto, mesmo aproximado, ou id.")


class PromocaoAtiva(BaseModel):
    nome: str
    desconto_percentual: str


class ProdutoDetalhe(BaseModel):
    id: int
    nome: str
    categoria: str | None
    descricao: str
    specs: dict
    situacao: str
    a_venda: bool
    preco_tabela: str | None
    preco_atual: str | None
    promocao_ativa: PromocaoAtiva | None


class Pagamento(BaseModel):
    pix: str
    pix_nao_acumula: bool


class Candidato(BaseModel):
    id: int
    nome: str


class SaidaDetalhesProduto(BaseModel):
    resultado: str
    produto: ProdutoDetalhe | None = None
    pagamento: Pagamento | None = None
    candidatos: list[Candidato] = []
    alternativas: list[ProdutoResumo] = []


def _detalhar(produto: Produto) -> ProdutoDetalhe:
    promocao = produto.promocao_ativa
    tem_preco = produto.preco is not None
    return ProdutoDetalhe(
        id=produto.id,
        nome=produto.nome,
        categoria=produto.categoria,
        descricao=produto.descricao,
        specs=produto.specs,
        situacao=produto.situacao,
        a_venda=produto.situacao == "disponivel",
        preco_tabela=formatar_brl(produto.preco) if tem_preco else None,
        preco_atual=formatar_brl(produto.preco_atual) if tem_preco else None,
        promocao_ativa=(
            PromocaoAtiva(
                nome=promocao.nome,
                desconto_percentual=formatar_percentual(promocao.desconto),
            )
            if promocao
            else None
        ),
    )


def _pagamento(produto: Produto) -> Pagamento | None:
    if produto.situacao not in {"disponivel", "temporariamente_indisponivel"}:
        return None
    promocao = produto.promocao_ativa
    pix = calcular_pix(produto.preco, promocao.desconto if promocao else None)
    return Pagamento(pix=formatar_brl(pix.valor), pix_nao_acumula=pix.nao_acumula)


@REGISTRO.ferramenta(
    "detalhes_produto",
    "Preço, situação, pagamento e alternativas de um produto específico.",
    ArgsDetalhesProduto,
)
def detalhes_produto(
    args: ArgsDetalhesProduto, ctx: Contexto
) -> SaidaDetalhesProduto:
    encontrado = ctx.repo.buscar_referencia(args.referencia)
    if encontrado.tipo != "encontrado":
        return SaidaDetalhesProduto(
            resultado=encontrado.tipo,
            candidatos=[
                Candidato(id=p.id, nome=p.nome) for p in encontrado.candidatos
            ],
        )
    produto = encontrado.produto
    return SaidaDetalhesProduto(
        resultado="encontrado",
        produto=_detalhar(produto),
        pagamento=_pagamento(produto),
        alternativas=[resumir_produto(p) for p in ctx.repo.alternativas(produto)],
    )


class ArgsConsultarPolitica(BaseModel):
    topico: Topico = Field(description="Seção do manual da loja.")


class SaidaConsultarPolitica(BaseModel):
    topico: str
    texto: str


@REGISTRO.ferramenta(
    "consultar_politica",
    "Devolve uma seção do manual: dados da loja, horário, pagamento, trocas, "
    "frete, promoções, atendimento, garantia ou privacidade.",
    ArgsConsultarPolitica,
)
def consultar_politica(
    args: ArgsConsultarPolitica, ctx: Contexto
) -> SaidaConsultarPolitica:
    return SaidaConsultarPolitica(
        topico=args.topico, texto=ctx.politicas.texto(args.topico)
    )
