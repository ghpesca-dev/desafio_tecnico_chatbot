"""Interface de linha de comando."""

import argparse
import logging
import sys

from rich.console import Console
from rich.markdown import Markdown

from emporio.agent import Agent, criar_cliente
from emporio.config import (
    PASTA_DADOS,
    ConfiguracaoInvalida,
    carregar_config,
    criar_relogio,
)
from emporio.data.loader import DadosInvalidos, carregar_dados
from emporio.data.repository import Repository
from emporio.session import SessionState
from emporio.tools import REGISTRO

COMANDOS_SAIDA = {"sair", "exit", "quit"}


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="emporio", description="Atendimento da Empório da Música"
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
    )


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
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    if args.debug:
        logging.getLogger("emporio").setLevel(logging.DEBUG)

    try:
        agente = criar_agente(args.data)
    except (ConfiguracaoInvalida, DadosInvalidos) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1

    conversar(agente, Console())
    return 0


if __name__ == "__main__":
    sys.exit(main())
