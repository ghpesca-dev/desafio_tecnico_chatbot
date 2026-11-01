"""Estado de uma conversa. O modelo não lê nem altera este objeto."""

import uuid
from dataclasses import dataclass, field


@dataclass
class SessionState:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mensagens: list[dict] = field(default_factory=list)
    pedidos_confirmados: set[int] = field(default_factory=set)
    falhas_confirmacao: int = 0
    mensagens_cliente_recentes: list[str] = field(default_factory=list)

    def registrar_mensagem_cliente(self, texto: str) -> None:
        self.mensagens.append({"role": "user", "content": texto})
        self.mensagens_cliente_recentes.append(texto)

    def cortar_janela(self, trocas: int) -> None:
        """Mantém as últimas trocas, sempre a partir de uma mensagem do cliente.

        Cortar em outro ponto separaria uma chamada de ferramenta do resultado,
        o que os provedores recusam.
        """
        inicios = [
            i for i, m in enumerate(self.mensagens) if m["role"] == "user"
        ]
        if len(inicios) > trocas:
            del self.mensagens[: inicios[-trocas]]

    def marca(self) -> int:
        return len(self.mensagens)

    def desfazer_ate(self, marca: int) -> None:
        del self.mensagens[marca:]
