"""API HTTP opcional e dashboard de demonstração. Não tem autenticação."""

import logging
import threading
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, StringConstraints

from emporio.agent import Agent
from emporio.cli import criar_agente
from emporio.config import FUSO, PASTA_CONVERSAS
from emporio.historico import Historico
from emporio.session import SessionState

logger = logging.getLogger("emporio.api")

PAGINA = Path(__file__).parent / "static" / "dashboard.html"


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
    apagada: bool = False


def agora() -> str:
    """Relógio real: com data fixada, o histórico sairia de ordem entre dias."""
    return datetime.now(FUSO).isoformat(timespec="milliseconds")


def criar_app(
    agente: Agent | None = None, historico: Historico | None = None
) -> FastAPI:
    sessoes: dict[str, Sessao] = {}
    trava_sessoes = threading.Lock()

    @asynccontextmanager
    async def ciclo(app: FastAPI) -> AsyncIterator[None]:
        app.state.agente = agente or criar_agente(None)
        app.state.historico = historico or Historico(PASTA_CONVERSAS)
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

    def somente_leitura(conversa_id: str) -> bool:
        """Sessões não voltam do disco, então confirmações de identidade também não."""
        with trava_sessoes:
            return conversa_id not in sessoes

    @app.get("/", include_in_schema=False)
    def pagina() -> FileResponse:
        return FileResponse(PAGINA, media_type="text/html")

    @app.post("/chat")
    def chat(entrada: Entrada) -> Saida:
        sessao = obter_sessao(entrada.session_id)
        with sessao.trava:
            if sessao.apagada:
                raise HTTPException(status_code=404, detail="Sessão desconhecida")
            inicio = agora()
            cronometro = time.perf_counter()
            resposta = app.state.agente.responder(sessao.estado, entrada.mensagem)
            tempo_ms = round((time.perf_counter() - cronometro) * 1000)
            try:
                app.state.historico.registrar_troca(
                    sessao.estado.id,
                    texto=entrada.mensagem,
                    resposta=resposta,
                    momento_cliente=inicio,
                    momento_agente=agora(),
                    tempo_ms=tempo_ms,
                    consultas=sessao.estado.consultas_turno,
                )
            except OSError as erro:
                logger.warning("Falha ao gravar a conversa: %s", type(erro).__name__)
        return Saida(session_id=sessao.estado.id, resposta=resposta)

    @app.get("/conversas")
    def conversas() -> dict:
        lidas = app.state.historico.listar()
        return {
            "data_referencia": app.state.agente.data_referencia,
            "conversas": [
                {
                    "id": conversa["id"],
                    "titulo": conversa["titulo"],
                    "atualizada_em": conversa["atualizada_em"],
                    "somente_leitura": somente_leitura(conversa["id"]),
                }
                for conversa in lidas
            ],
            "indicadores": app.state.historico.indicadores(lidas),
        }

    @app.get("/conversas/{conversa_id}")
    def conversa(conversa_id: str) -> dict:
        lida = app.state.historico.obter(conversa_id)
        if lida is None:
            raise HTTPException(status_code=404, detail="Conversa desconhecida")
        return {**lida, "somente_leitura": somente_leitura(conversa_id)}

    @app.delete("/conversas/{conversa_id}", status_code=204)
    def apagar(conversa_id: str) -> Response:
        with trava_sessoes:
            sessao = sessoes.get(conversa_id)
        if sessao is not None:
            # Espera a resposta em andamento, para ela não recriar o arquivo.
            with sessao.trava:
                sessao.apagada = True
                with trava_sessoes:
                    sessoes.pop(conversa_id, None)
        if not app.state.historico.remover(conversa_id) and sessao is None:
            raise HTTPException(status_code=404, detail="Conversa desconhecida")
        return Response(status_code=204)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = criar_app()
