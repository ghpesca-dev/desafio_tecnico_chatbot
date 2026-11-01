import re


def test_reclamacao_pede_contato_registra_e_informa_prazo(conversa):
    resposta = conversa.enviar("Quero reclamar do atendimento, fui muito mal atendido")

    assert "registrar_reclamacao" not in conversa.ferramentas
    assert re.search(r"contato|e-mail|email|telefone", resposta.lower())

    resposta = conversa.enviar(
        "O vendedor foi grosseiro comigo no WhatsApp ontem. "
        "Pode falar comigo no maria@teste.com"
    )

    assert "registrar_reclamacao" in conversa.ferramentas
    assert "24 horas" in resposta
    registrada = conversa.agente._reclamacoes.listar()[0]
    assert registrada.contato == "maria@teste.com"
    assert registrada.resumo.strip()


def test_pergunta_nao_coberta_encaminha(conversa):
    resposta = conversa.enviar(
        "Vocês dão desconto para uma escola que comprar 20 violões de uma vez?"
    )
    assert "3341-4444" in resposta
    conversa.auditar_valores(resposta)


def test_fora_do_horario_informa_a_volta(conversa_noite):
    resposta = conversa_noite.enviar(
        "Preciso falar com alguém da equipe sobre um desconto para escola"
    )

    assert "3341-4444" in resposta
    assert re.search(r"\b0?9(:00|h)", resposta)
    assert re.search(r"amanhã|sábado", resposta.lower())
