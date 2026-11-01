"""Laço de tool use e histórico da conversa."""

import json
import logging
import re
import time
from collections.abc import Callable
from datetime import datetime

import openai

from emporio.config import BASE_URL, Config
from emporio.data.repository import Repository
from emporio.policies import Politicas
from emporio.prompts import montar_system_prompt
from emporio.session import SessionState
from emporio.tools import Contexto, Registro

logger = logging.getLogger("emporio.agente")

FALLBACK = (
    "Puxa, não consegui resolver isso por aqui. Para não te deixar sem resposta, "
    "fala com a nossa equipe pelo (67) 3341-4444 ou pelo e-mail "
    "contato@emporiodamusica.com.br."
)
CAMPOS_MASCARADOS = {"contato"}

# O turno termina na mensagem: quem promete consultar sem chamar uma ferramenta
# deixa o cliente sem resposta. O prompt reduz isso, mas não garante.
PROMESSA_DE_CONSULTA = re.compile(
    r"\b(vou|deixa eu|deixe-me)\s+(te\s+)?"
    r"(verificar|consultar|checar|conferir|olhar|buscar|procurar|ver)\b"
    r"|\bum (minuto|minutinho|instante|momento)\b",
    re.IGNORECASE,
)


def criar_cliente(config: Config) -> openai.OpenAI:
    return openai.OpenAI(
        base_url=BASE_URL,
        api_key=config.api_key,
        timeout=config.timeout_s,
        max_retries=config.max_retries,
    )


def mascarar_argumentos(argumentos: str) -> str:
    """Versão de log dos argumentos, sem dados de contato."""
    try:
        dados = json.loads(argumentos or "{}")
    except json.JSONDecodeError:
        return "<argumentos inválidos>"
    if not isinstance(dados, dict):
        return "<argumentos inválidos>"
    return json.dumps(
        {k: "***" if k in CAMPOS_MASCARADOS else v for k, v in dados.items()},
        ensure_ascii=False,
    )


class Agent:
    def __init__(
        self,
        cliente,
        config: Config,
        registro: Registro,
        repo: Repository | None,
        relogio: Callable[[], datetime],
        politicas: Politicas | None = None,
    ):
        self._cliente = cliente
        self._config = config
        self._registro = registro
        self._repo = repo
        self._relogio = relogio
        self._politicas = politicas

    def responder(self, sessao: SessionState, texto: str) -> str:
        sessao.registrar_mensagem_cliente(texto)
        sessao.cortar_janela(self._config.janela_trocas)
        # Calculada depois do corte, que muda os índices do histórico.
        marca = sessao.marca() - 1

        consultou = False
        exigir_ferramenta = False
        ja_exigiu = False

        for _ in range(self._config.max_iteracoes):
            try:
                mensagem = self._chamar_llm(sessao, exigir_ferramenta)
            except (openai.OpenAIError, ValueError) as erro:
                logger.warning(
                    "Falha na chamada ao LLM: %s",
                    type(erro).__name__,
                    exc_info=logger.isEnabledFor(logging.DEBUG),
                )
                sessao.desfazer_ate(marca)
                return FALLBACK

            if not mensagem.tool_calls:
                conteudo = (mensagem.content or "").strip()
                if not conteudo:
                    sessao.desfazer_ate(marca)
                    return FALLBACK
                if (
                    not consultou
                    and not ja_exigiu
                    and PROMESSA_DE_CONSULTA.search(conteudo)
                ):
                    logger.debug("Promessa de consulta sem ferramenta: repetindo")
                    exigir_ferramenta = ja_exigiu = True
                    continue
                sessao.mensagens.append({"role": "assistant", "content": conteudo})
                return conteudo

            self._executar_chamadas(sessao, mensagem)
            consultou = True
            exigir_ferramenta = False

        logger.warning("Limite de %s iterações atingido", self._config.max_iteracoes)
        sessao.mensagens.append({"role": "assistant", "content": FALLBACK})
        return FALLBACK

    def _chamar_llm(self, sessao: SessionState, exigir_ferramenta: bool = False):
        system = montar_system_prompt(self._relogio())
        parametros = {
            "model": self._config.modelo,
            "messages": [{"role": "system", "content": system}, *sessao.mensagens],
            # Sem isto, um provedor sem ferramentas responderia sem consultar nada.
            "extra_body": {"provider": {"require_parameters": True}},
        }
        ferramentas = self._registro.schemas()
        if ferramentas:
            parametros["tools"] = ferramentas
        if self._config.temperatura is not None:
            parametros["temperature"] = self._config.temperatura
        if exigir_ferramenta and ferramentas:
            parametros["tool_choice"] = "required"

        resposta = self._cliente.chat.completions.create(**parametros)
        if not resposta.choices:
            raise ValueError("Resposta do LLM sem choices")
        return resposta.choices[0].message

    def _executar_chamadas(self, sessao: SessionState, mensagem) -> None:
        sessao.mensagens.append(
            {
                "role": "assistant",
                "content": mensagem.content,
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {
                            "name": c.function.name,
                            "arguments": c.function.arguments,
                        },
                    }
                    for c in mensagem.tool_calls
                ],
            }
        )
        contexto = Contexto(
            self._repo, sessao, self._relogio().date(), self._politicas
        )
        for chamada in mensagem.tool_calls:
            inicio = time.perf_counter()
            resultado = self._registro.despachar(
                chamada.function.name, chamada.function.arguments, contexto
            )
            logger.debug(
                "ferramenta=%s args=%s duracao_ms=%.1f",
                chamada.function.name,
                mascarar_argumentos(chamada.function.arguments),
                (time.perf_counter() - inicio) * 1000,
            )
            sessao.mensagens.append(
                {
                    "role": "tool",
                    "tool_call_id": chamada.id,
                    "content": resultado,
                }
            )
