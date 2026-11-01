"""Ferramentas expostas ao LLM: schemas, despacho e implementações."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints, ValidationError

from emporio.complaints import Reclamacoes
from emporio.data.repository import Pedido, Produto, Promocao, Repository
from emporio.policies import Politicas, Topico
from emporio.rules import (
    calcular_pix,
    calcular_prazos,
    formatar_brl,
    formatar_percentual,
    tabela_parcelas,
)
from emporio.session import SessionState

logger = logging.getLogger("emporio.ferramentas")


@dataclass
class Contexto:
    """Dependências de uma execução; o modelo nunca as controla."""

    repo: Repository | None
    sessao: SessionState
    data_referencia: date
    politicas: Politicas | None = None
    reclamacoes: Reclamacoes | None = None
    agora: datetime | None = None


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

ORIENTACAO_NAO_ENCONTRADO = (
    "Diga que não encontrou no catálogo, sem supor o motivo, e ofereça o "
    "contato da loja: (67) 3341-4444."
)


class ProdutoResumo(BaseModel):
    id: int
    nome: str
    categoria: str
    preco_atual: str
    preco_original: str | None
    desconto_percentual: str | None
    preco_exibicao: str
    promocao: str | None
    disponivel: bool


def resumir_produto(produto: Produto) -> ProdutoResumo:
    promocao = produto.promocao_ativa
    atual = formatar_brl(produto.preco_atual)
    exibicao = atual
    if promocao:
        exibicao = (
            f"{atual} (de {formatar_brl(produto.preco)}, "
            f"{formatar_percentual(promocao.desconto)} de desconto)"
        )
    return ProdutoResumo(
        id=produto.id,
        nome=produto.nome,
        categoria=produto.categoria,
        preco_atual=atual,
        preco_original=formatar_brl(produto.preco) if promocao else None,
        desconto_percentual=(
            formatar_percentual(promocao.desconto) if promocao else None
        ),
        preco_exibicao=exibicao,
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
    em_promocao: bool = Field(False, description="Só produtos em promoção ativa.")


class PromocaoEncontrada(BaseModel):
    nome: str
    ativa: bool


class SaidaBuscarProdutos(BaseModel):
    total_encontrado: int
    exibidos: int
    categoria_resolvida: str | None
    categoria_sem_itens: bool
    produtos: list[ProdutoResumo]
    promocao_encontrada: PromocaoEncontrada | None = None
    orientacao: str | None = None


@REGISTRO.ferramenta(
    "buscar_produtos",
    "Lista produtos disponíveis por tipo, nome, marca, faixa de preço ou promoção. "
    "Em `texto`, aceita o nome de uma campanha, como Black Friday.",
    ArgsBuscarProdutos,
)
def buscar_produtos(args: ArgsBuscarProdutos, ctx: Contexto) -> SaidaBuscarProdutos:
    encontrada = ctx.repo.promocao_por_nome(args.texto) if args.texto else None
    campanha_ativa = encontrada is not None and encontrada.ativa
    resultado = ctx.repo.buscar_produtos(
        categoria=args.categoria,
        texto=None if campanha_ativa else args.texto,
        preco_min=args.preco_min,
        preco_max=args.preco_max,
        em_promocao=args.em_promocao,
        promocao=encontrada.nome if campanha_ativa else None,
    )
    return SaidaBuscarProdutos(
        total_encontrado=resultado.total,
        exibidos=len(resultado.produtos),
        categoria_resolvida=", ".join(c.nome for c in resultado.categorias) or None,
        categoria_sem_itens=resultado.categoria_sem_itens,
        produtos=[resumir_produto(p) for p in resultado.produtos],
        promocao_encontrada=(
            PromocaoEncontrada(nome=encontrada.nome, ativa=encontrada.ativa)
            if encontrada
            else None
        ),
        orientacao=(
            ORIENTACAO_NAO_ENCONTRADO
            if not (resultado.total or resultado.categoria_sem_itens or encontrada)
            else None
        ),
    )


class ArgsDetalhesProduto(BaseModel):
    referencia: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ] = Field(description="Nome do produto, mesmo aproximado, ou id.")


class PromocaoResumo(BaseModel):
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
    promocao_ativa: PromocaoResumo | None
    promocao_encerrada: PromocaoResumo | None


class ParcelaSaida(BaseModel):
    vezes: int
    valor: str


class Pagamento(BaseModel):
    pix: str
    pix_nao_acumula: bool
    parcelas: list[ParcelaSaida]
    parcelas_sem_juros: bool = True  # Manual, 3.1: até 12x, todas sem juros.
    max_parcelas: int


class Candidato(BaseModel):
    id: int
    nome: str


class SaidaDetalhesProduto(BaseModel):
    resultado: str
    produto: ProdutoDetalhe | None = None
    pagamento: Pagamento | None = None
    candidatos: list[Candidato] = []
    alternativas: list[ProdutoResumo] = []
    orientacao: str | None = None


def _resumir_promocao(promocao: Promocao | None) -> PromocaoResumo | None:
    if promocao is None:
        return None
    return PromocaoResumo(
        nome=promocao.nome,
        desconto_percentual=formatar_percentual(promocao.desconto),
    )


def _detalhar(produto: Produto) -> ProdutoDetalhe:
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
        promocao_ativa=_resumir_promocao(produto.promocao_ativa),
        promocao_encerrada=_resumir_promocao(produto.promocao_encerrada),
    )


def _pagamento(produto: Produto) -> Pagamento | None:
    if produto.situacao not in {"disponivel", "temporariamente_indisponivel"}:
        return None
    promocao = produto.promocao_ativa
    pix = calcular_pix(produto.preco, promocao.desconto if promocao else None)
    tabela = tabela_parcelas(produto.preco_atual)
    return Pagamento(
        pix=formatar_brl(pix.valor),
        pix_nao_acumula=pix.nao_acumula,
        parcelas=[
            ParcelaSaida(vezes=p.vezes, valor=formatar_brl(p.valor))
            for p in tabela.parcelas
        ],
        max_parcelas=tabela.max_parcelas,
    )


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
            orientacao=(
                ORIENTACAO_NAO_ENCONTRADO
                if encontrado.tipo == "nao_encontrado"
                else None
            ),
        )
    produto = encontrado.produto
    return SaidaDetalhesProduto(
        resultado="encontrado",
        produto=_detalhar(produto),
        pagamento=_pagamento(produto),
        alternativas=[resumir_produto(p) for p in ctx.repo.alternativas(produto)],
    )


ORIENTACAO_PEDIDO = {
    "precisa_confirmacao": (
        "Peça o e-mail ou o telefone cadastrado no pedido, sem dizer se ele existe."
    ),
    "nao_confirmado": (
        "Diga que não foi possível confirmar os dados, sem dizer se o pedido "
        "existe, e peça para conferir o número e o contato."
    ),
    "bloqueado": (
        "Diga que não dá para tentar de novo por aqui e indique o contato da "
        "loja: (67) 3341-4444."
    ),
}


class ArgsConsultarPedido(BaseModel):
    numero_pedido: int = Field(description="Número do pedido.")
    contato: str | None = Field(
        None,
        description=(
            "E-mail ou telefone exatamente como o cliente escreveu. Omita se ele "
            "não informou."
        ),
    )


class ItemSaida(BaseModel):
    nome: str
    quantidade: int


class PrazoSaida(BaseModel):
    situacao: str
    ate: date | None
    base: str


class PedidoSaida(BaseModel):
    numero: int
    primeiro_nome: str | None
    status: str
    data: date | None
    total: str | None
    pagamento: str
    rastreio: str | None
    previsao_entrega: date | None
    motivo_cancelamento: str | None
    itens: list[ItemSaida]
    prazos: dict[str, PrazoSaida]


class SaidaConsultarPedido(BaseModel):
    resultado: str
    pedido: PedidoSaida | None = None
    orientacao: str | None = None


def _negar(resultado: str) -> SaidaConsultarPedido:
    return SaidaConsultarPedido(
        resultado=resultado, orientacao=ORIENTACAO_PEDIDO[resultado]
    )


def _pedido_saida(pedido: Pedido, hoje: date) -> PedidoSaida:
    prazos = calcular_prazos(
        pedido.status_codigo, pedido.data_compra, pedido.previsao_entrega, hoje
    )
    return PedidoSaida(
        numero=pedido.numero,
        primeiro_nome=pedido.primeiro_nome,
        status=pedido.status,
        data=pedido.data_compra,
        total=formatar_brl(pedido.total) if pedido.total is not None else None,
        pagamento=pedido.pagamento,
        rastreio=pedido.rastreio,
        previsao_entrega=pedido.previsao_entrega,
        motivo_cancelamento=pedido.motivo_cancelamento,
        itens=[ItemSaida(nome=i.nome, quantidade=i.quantidade) for i in pedido.itens],
        prazos={
            nome: PrazoSaida(situacao=p.situacao, ate=p.ate, base=p.base)
            for nome, p in prazos.items()
        },
    )


@REGISTRO.ferramenta(
    "consultar_pedido",
    "Status, rastreio, previsão, itens e prazos de troca de um pedido. Só devolve "
    "os dados depois de confirmar o e-mail ou o telefone do cadastro.",
    ArgsConsultarPedido,
)
def consultar_pedido(args: ArgsConsultarPedido, ctx: Contexto) -> SaidaConsultarPedido:
    """A ordem das verificações é a regra: nada aqui depende do modelo."""
    sessao = ctx.sessao
    numero = args.numero_pedido
    if numero not in sessao.pedidos_confirmados:
        if sessao.bloqueada:
            return _negar("bloqueado")
        contato = (args.contato or "").strip()
        if not contato or not sessao.cliente_escreveu(contato):
            return _negar("precisa_confirmacao")
        if not ctx.repo.pedido_confere(numero, contato):
            sessao.registrar_falha_confirmacao()
            return _negar("bloqueado" if sessao.bloqueada else "nao_confirmado")
        sessao.confirmar_pedido(numero)
    return SaidaConsultarPedido(
        resultado="ok",
        pedido=_pedido_saida(ctx.repo.dados_pedido(numero), ctx.data_referencia),
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


TextoObrigatorio = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1)
]


class ArgsRegistrarReclamacao(BaseModel):
    resumo: TextoObrigatorio = Field(description="Resumo da reclamação.")
    contato: TextoObrigatorio = Field(
        description="E-mail ou telefone para retorno, informado pelo cliente."
    )
    nome: str | None = Field(None, description="Nome do cliente, se ele informou.")
    numero_pedido: int | None = Field(None, description="Pedido relacionado, se houver.")


class SaidaRegistrarReclamacao(BaseModel):
    registrada: bool
    protocolo: str | None = None


@REGISTRO.ferramenta(
    "registrar_reclamacao",
    "Registra uma reclamação para a equipe retornar ao cliente. Exige o resumo e "
    "um contato informado pelo cliente.",
    ArgsRegistrarReclamacao,
)
def registrar_reclamacao(
    args: ArgsRegistrarReclamacao, ctx: Contexto
) -> SaidaRegistrarReclamacao:
    try:
        reclamacao = ctx.reclamacoes.registrar(
            sessao_id=ctx.sessao.id,
            resumo=args.resumo,
            contato=args.contato,
            momento=ctx.agora,
            nome=args.nome,
            pedido=args.numero_pedido,
        )
    except OSError:
        logger.exception("Falha ao gravar reclamação")
        return SaidaRegistrarReclamacao(registrada=False)
    return SaidaRegistrarReclamacao(registrada=True, protocolo=reclamacao.id)
