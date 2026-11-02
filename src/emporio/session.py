"""Estado de uma conversa. O modelo não lê nem altera este objeto."""

import uuid
from dataclasses import dataclass, field

from emporio.rules import digitos_telefone

LIMITE_FALHAS_CONFIRMACAO = 3


@dataclass
class SessionState:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mensagens: list[dict] = field(default_factory=list)
    pedidos_confirmados: set[int] = field(default_factory=set)
    falhas_confirmacao: int = 0
    mensagens_cliente_recentes: list[str] = field(default_factory=list)
    # Consultas do turno atual, para o dashboard. Não vão ao modelo.
    consultas_turno: list[dict] = field(default_factory=list)

    def registrar_mensagem_cliente(self, texto: str) -> None:
        self.mensagens.append({"role": "user", "content": texto})
        self.mensagens_cliente_recentes.append(texto)

    @property
    def bloqueada(self) -> bool:
        return self.falhas_confirmacao >= LIMITE_FALHAS_CONFIRMACAO

    def registrar_falha_confirmacao(self) -> None:
        self.falhas_confirmacao += 1

    def cliente_escreveu(self, contato: str) -> bool:
        """O contato precisa ter vindo do cliente, não do modelo.

        Vale só o que foi escrito depois da última confirmação, para que um
        pedido confirmado não abra outro sem o cliente repetir o dado.
        """
        texto = contato.strip().lower()
        digitos = digitos_telefone(texto)
        return bool(texto) and any(
            texto in mensagem.lower()
            or (digitos and digitos in digitos_telefone(mensagem))
            for mensagem in self.mensagens_cliente_recentes
        )

    def confirmar_pedido(self, numero: int) -> None:
        self.pedidos_confirmados.add(numero)
        self.mensagens_cliente_recentes.clear()

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
