"""API HTTP opcional, com as mesmas regras da CLI. Não tem autenticação."""

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, StringConstraints

from emporio.agent import Agent
from emporio.cli import criar_agente
from emporio.session import SessionState


class Entrada(BaseModel):
    session_id: str | None = None
    mensagem: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Saida(BaseModel):
    session_id: str
    resposta: str


@dataclass
class Sessao:
    estado: SessionState = field(default_factory=SessionState)
    trava: threading.Lock = field(default_factory=threading.Lock)


def criar_app(agente: Agent | None = None) -> FastAPI:
    sessoes: dict[str, Sessao] = {}
    trava_sessoes = threading.Lock()

    @asynccontextmanager
    async def ciclo(app: FastAPI) -> AsyncIterator[None]:
        app.state.agente = agente or criar_agente(None)
        yield

    app = FastAPI(title="Empório da Música", lifespan=ciclo)

    def obter_sessao(session_id: str | None) -> Sessao:
        with trava_sessoes:
            if session_id is None:
                sessao = Sessao()
                sessoes[sessao.estado.id] = sessao
                return sessao
            sessao = sessoes.get(session_id)
        if sessao is None:
            raise HTTPException(status_code=404, detail="Sessão desconhecida")
        return sessao

    @app.post("/chat")
    def chat(entrada: Entrada) -> Saida:
        sessao = obter_sessao(entrada.session_id)
        with sessao.trava:
            resposta = app.state.agente.responder(sessao.estado, entrada.mensagem)
        return Saida(session_id=sessao.estado.id, resposta=resposta)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = criar_app()
