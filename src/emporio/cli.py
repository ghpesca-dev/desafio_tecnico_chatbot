"""Interface de linha de comando."""

import argparse
import logging
import sys
from datetime import datetime

from rich.console import Console
from rich.markdown import Markdown

from emporio.agent import Agent, criar_cliente
from emporio.complaints import Reclamacoes
from emporio.config import (
    ARQUIVO_RECLAMACOES,
    PASTA_DADOS,
    PASTA_POLITICAS,
    ConfiguracaoInvalida,
    carregar_config,
    criar_relogio,
)
from emporio.data.loader import DadosInvalidos, carregar_dados
from emporio.data.repository import Repository
from emporio.policies import Politicas, PoliticasInvalidas
from emporio.session import SessionState
from emporio.tools import REGISTRO

COMANDOS_SAIDA = {"sair", "exit", "quit"}


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="emporio", description="Atendimento da Empório da Música"
    )
    parser.add_argument(
        "comando",
        nargs="?",
        choices=["reclamacoes"],
        help="lista as reclamações registradas, para a equipe",
    )
    parser.add_argument("--data", help="fixa a data de referência (AAAA-MM-DD)")
    parser.add_argument(
        "--debug", action="store_true", help="mostra as chamadas de ferramenta"
    )
    return parser


def criar_agente(data_cli: str | None) -> Agent:
    config = carregar_config(data_cli)
    if not config.api_key:
        raise ConfiguracaoInvalida(
            "OPENROUTER_API_KEY não configurada. Copie .env.example para .env "
            "e preencha a chave."
        )
    return Agent(
        cliente=criar_cliente(config),
        config=config,
        registro=REGISTRO,
        repo=Repository(carregar_dados(PASTA_DADOS)),
        relogio=criar_relogio(config.data_referencia),
        politicas=Politicas(PASTA_POLITICAS),
        reclamacoes=Reclamacoes(ARQUIVO_RECLAMACOES),
    )


def listar_reclamacoes(console: Console) -> None:
    registros = Reclamacoes(ARQUIVO_RECLAMACOES).listar()
    if not registros:
        console.print("Nenhuma reclamação registrada.")
        return
    for r in registros:
        momento = datetime.fromisoformat(r.registrada_em).strftime("%d/%m/%Y %H:%M")
        extras = " | ".join(
            texto
            for texto in (r.nome, f"pedido {r.pedido}" if r.pedido else None)
            if texto
        )
        console.print(f"[bold]{momento}[/bold] {r.contato} {extras}", markup=True)
        console.print(r.resumo, markup=False, highlight=False)
        console.print()


def conversar(agente: Agent, console: Console) -> None:
    sessao = SessionState()
    console.print("[bold]Empório da Música[/bold]. Digite [cyan]sair[/cyan] para encerrar.\n")
    while True:
        try:
            texto = console.input("[bold cyan]Você:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return
        if not texto:
            continue
        if texto.lower() in COMANDOS_SAIDA:
            return
        with console.status("Consultando..."):
            resposta = agente.responder(sessao, texto)
        console.print("[bold green]Empório:[/bold green]")
        console.print(Markdown(resposta))
        console.print()


def main(argv: list[str] | None = None) -> int:
    args = criar_parser().parse_args(argv)
    if args.comando == "reclamacoes":
        listar_reclamacoes(Console())
        return 0
    # Avisos de dados e falhas tratadas só interessam em depuração: o cliente
    # recebe a mensagem amigável.
    logging.basicConfig(
        level=logging.ERROR,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    if args.debug:
        logging.getLogger("emporio").setLevel(logging.DEBUG)

    try:
        agente = criar_agente(args.data)
    except (ConfiguracaoInvalida, DadosInvalidos, PoliticasInvalidas) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    conversar(agente, Console())
    return 0


if __name__ == "__main__":
    sys.exit(main())
