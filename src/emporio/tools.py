"""Ferramentas expostas ao LLM: schemas, despacho e implementações."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import BaseModel, ValidationError

from emporio.data.repository import Repository
from emporio.session import SessionState

logger = logging.getLogger("emporio.ferramentas")


@dataclass
class Contexto:
    """Dependências de uma execução; o modelo nunca as controla."""

    repo: Repository | None
    sessao: SessionState
    data_referencia: date


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
