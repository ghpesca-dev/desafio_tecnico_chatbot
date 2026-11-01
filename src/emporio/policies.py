"""Carga das seções do manual, convertidas por scripts/extract_policies.py."""

from pathlib import Path
from typing import Literal, get_args

Topico = Literal[
    "loja",
    "horario",
    "pagamento",
    "trocas_devolucoes",
    "frete",
    "promocoes",
    "atendimento",
    "garantia",
    "privacidade",
]
TOPICOS: tuple[str, ...] = get_args(Topico)


class PoliticasInvalidas(Exception):
    """As seções do manual não permitem iniciar o agente."""


class Politicas:
    def __init__(self, pasta: Path):
        self._textos: dict[str, str] = {}
        problemas = []
        for topico in TOPICOS:
            caminho = Path(pasta) / f"{topico}.md"
            texto = caminho.read_text(encoding="utf-8") if caminho.exists() else ""
            if texto.strip():
                self._textos[topico] = texto
            else:
                problemas.append(topico)
        if problemas:
            raise PoliticasInvalidas(
                f"Seções do manual faltando ou vazias: {', '.join(problemas)}"
            )

    def texto(self, topico: str) -> str:
        return self._textos[topico]
