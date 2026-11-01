"""SC-002, SC-008 e SC-009: 30 perguntas, com valores conferidos pelas fontes."""

import math
import re
import time

import pytest

from emporio.rules import calcular_pix, formatar_brl

LIMITE_P95_S = 10
MINIMO_SEM_EQUIPE = 0.8
PRECOS = [95, 90, 94, 127, 88, 100, 110, 120]
PIX = [95, 100, 110, 120, 88, 92]
PROMOCOES = [90, 94, 121, 127]
SITUACOES = [
    (96, r"indispon"),
    (113, r"cat[aá]logo"),
    (136, r"cat[aá]logo"),
    (130, r"em breve|ainda n[aã]o"),
]
POLITICAS = [
    ("Qual o prazo para desistir de uma compra online?", "7"),
    ("Em quantos dias posso trocar um produto com defeito?", "30"),
    ("Quanto tempo de garantia legal tenho?", "90"),
    ("A partir de quanto o frete é grátis em Campo Grande?", "500"),
    ("Até que horas vocês abrem no sábado?", "13"),
    ("Em quanto tempo sai o reembolso?", "10"),
    ("Em até quantas vezes vocês parcelam?", "12"),
    ("Qual o desconto no PIX?", "5%"),
]
CASOS = (
    [("preco", i) for i in PRECOS]
    + [("pix", i) for i in PIX]
    + [("promocao", i) for i in PROMOCOES]
    + [("situacao", i) for i in range(len(SITUACOES))]
    + [("politica", i) for i in range(len(POLITICAS))]
)
duracoes: list[float] = []
sem_equipe: list[bool] = []


def medir(conversa, pergunta):
    inicio = time.perf_counter()
    resposta = conversa.enviar(pergunta)
    duracoes.append(time.perf_counter() - inicio)
    sem_equipe.append("3341-4444" not in resposta)
    return resposta


def sem_prefixo(valor):
    return formatar_brl(valor).removeprefix("R$ ")


@pytest.mark.parametrize(("tipo", "indice"), CASOS)
def test_valor_coincide_com_a_fonte(conversa, repo, tipo, indice):
    if tipo == "politica":
        pergunta, trecho = POLITICAS[indice]
        resposta = medir(conversa, pergunta)
        assert "consultar_politica" in conversa.ferramentas
        assert trecho in resposta
    elif tipo == "situacao":
        numero, padrao = SITUACOES[indice]
        resposta = medir(conversa, f"Quero comprar o {repo.produto(numero).nome}")
        assert re.search(padrao, resposta.lower())
    else:
        produto = repo.produto(indice)
        if tipo == "preco":
            resposta = medir(conversa, f"Quanto custa o {produto.nome}?")
            assert sem_prefixo(produto.preco_atual) in resposta
        elif tipo == "pix":
            resposta = medir(conversa, f"Quanto fica o {produto.nome} no PIX?")
            assert sem_prefixo(calcular_pix(produto.preco, None).valor) in resposta
        else:
            resposta = medir(conversa, f"O {produto.nome} está em promoção?")
            assert sem_prefixo(produto.preco_atual) in resposta
            assert sem_prefixo(produto.preco) in resposta
    conversa.auditar_valores(resposta)


def test_zz_indicadores():
    if len(duracoes) < len(CASOS):
        pytest.skip("Exige todas as perguntas na mesma execução")

    ordenadas = sorted(duracoes)
    p95 = ordenadas[math.ceil(len(ordenadas) * 0.95) - 1]
    proporcao = sum(sem_equipe) / len(sem_equipe)
    print(f"\nP95={p95:.1f}s sem_equipe={proporcao:.0%}")

    assert p95 <= LIMITE_P95_S
    assert proporcao >= MINIMO_SEM_EQUIPE

