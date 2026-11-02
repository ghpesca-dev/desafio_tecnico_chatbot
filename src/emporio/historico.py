"""Histórico das conversas do dashboard.

Um arquivo JSON por conversa: apagar é remover o arquivo, e um arquivo danificado
não afeta os outros. Pode ter dados pessoais: fica fora do Git.
"""

import json
import logging
import os
import uuid
from collections import Counter
from pathlib import Path

logger = logging.getLogger("emporio.historico")

TAMANHO_TITULO = 60
TOTAL_CONSULTAS_MAIS_USADAS = 3


class Historico:
    def __init__(self, pasta: Path):
        self.pasta = Path(pasta)

    def _caminho(self, conversa_id: str) -> Path | None:
        """Só um UUID canônico vira caminho: o id vem de fora."""
        try:
            canonico = str(uuid.UUID(conversa_id))
        except (ValueError, AttributeError, TypeError):
            return None
        if canonico != conversa_id:
            return None
        return self.pasta / f"{canonico}.json"

    def registrar_troca(
        self,
        conversa_id: str,
        texto: str,
        resposta: str,
        momento_cliente: str,
        momento_agente: str,
        tempo_ms: int,
        consultas: list[dict],
    ) -> None:
        """Grava cliente e agente juntos, substituindo o arquivo de uma vez."""
        caminho = self._caminho(conversa_id)
        if caminho is None:
            raise ValueError("Identificador de conversa inválido")
        conversa = self._ler(caminho) or {
            "id": conversa_id,
            "titulo": texto[:TAMANHO_TITULO],
            "iniciada_em": momento_cliente,
            "mensagens": [],
        }
        conversa["atualizada_em"] = momento_agente
        conversa["mensagens"] += [
            {"autor": "cliente", "texto": texto, "momento": momento_cliente},
            {
                "autor": "agente",
                "texto": resposta,
                "momento": momento_agente,
                "tempo_ms": tempo_ms,
                "consultas": consultas,
            },
        ]
        self.pasta.mkdir(parents=True, exist_ok=True)
        temporario = caminho.with_suffix(".tmp")
        temporario.write_text(
            json.dumps(conversa, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporario, caminho)

    def _ler(self, caminho: Path) -> dict | None:
        if not caminho.exists():
            return None
        try:
            conversa = json.loads(caminho.read_text(encoding="utf-8"))
            valida = (
                conversa["id"] == caminho.stem
                and isinstance(conversa["titulo"], str)
                and isinstance(conversa["atualizada_em"], str)
                and all(isinstance(m["autor"], str) for m in conversa["mensagens"])
            )
        except (OSError, ValueError, KeyError, TypeError):
            valida = False
        if not valida:
            logger.warning("Arquivo de conversa ignorado: %s", caminho.name)
            return None
        return conversa

    def obter(self, conversa_id: str) -> dict | None:
        caminho = self._caminho(conversa_id)
        return self._ler(caminho) if caminho else None

    def listar(self) -> list[dict]:
        """Da mais recente para a mais antiga, sem os arquivos ilegíveis."""
        lidas = (self._ler(caminho) for caminho in self.pasta.glob("*.json"))
        return sorted(
            (conversa for conversa in lidas if conversa),
            key=lambda conversa: conversa["atualizada_em"],
            reverse=True,
        )

    def remover(self, conversa_id: str) -> bool:
        caminho = self._caminho(conversa_id)
        if caminho is None or not caminho.exists():
            return False
        caminho.unlink()
        return True

    def indicadores(self, conversas: list[dict]) -> dict:
        mensagens = [m for c in conversas for m in c["mensagens"]]
        respostas = [m for m in mensagens if m["autor"] == "agente"]
        tempos = [m["tempo_ms"] for m in respostas if "tempo_ms" in m]
        consultas = Counter(
            consulta["nome"] for m in respostas for consulta in m.get("consultas", [])
        )
        return {
            "conversas": len(conversas),
            "mensagens_cliente": sum(m["autor"] == "cliente" for m in mensagens),
            "tempo_medio_ms": round(sum(tempos) / len(tempos)) if tempos else 0,
            "consultas_mais_usadas": [
                {"nome": nome, "total": total}
                for nome, total in consultas.most_common(TOTAL_CONSULTAS_MAIS_USADAS)
            ],
        }
