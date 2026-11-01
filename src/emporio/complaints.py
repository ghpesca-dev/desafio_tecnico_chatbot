"""Registro de reclamações, para a equipe consultar depois da conversa."""

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("emporio.reclamacoes")


@dataclass(frozen=True)
class Reclamacao:
    id: str
    registrada_em: str
    sessao_id: str
    resumo: str
    contato: str
    nome: str | None = None
    pedido: int | None = None


class Reclamacoes:
    """Arquivo JSONL que só recebe acréscimos. Tem dados pessoais: fica fora do Git."""

    def __init__(self, caminho: Path):
        self.caminho = Path(caminho)

    def registrar(
        self,
        sessao_id: str,
        resumo: str,
        contato: str,
        momento: datetime,
        nome: str | None = None,
        pedido: int | None = None,
    ) -> Reclamacao:
        resumo, contato = resumo.strip(), contato.strip()
        if not resumo or not contato:
            raise ValueError("Resumo e contato são obrigatórios")
        reclamacao = Reclamacao(
            id=str(uuid.uuid4()),
            registrada_em=momento.isoformat(),
            sessao_id=sessao_id,
            resumo=resumo,
            contato=contato,
            nome=nome,
            pedido=pedido,
        )
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        with self.caminho.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(asdict(reclamacao), ensure_ascii=False) + "\n")
        return reclamacao

    def listar(self) -> list[Reclamacao]:
        """Da mais recente para a mais antiga."""
        if not self.caminho.exists():
            return []
        registros = []
        for numero, linha in enumerate(
            self.caminho.read_text(encoding="utf-8").splitlines(), start=1
        ):
            try:
                registros.append(Reclamacao(**json.loads(linha)))
            except (json.JSONDecodeError, TypeError):
                logger.warning("Linha %s de reclamações ignorada", numero)
        return registros[::-1]
