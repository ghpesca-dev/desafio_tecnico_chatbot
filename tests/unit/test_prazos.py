from datetime import date

import pytest

from emporio.rules import calcular_prazos

HOJE = date(2026, 2, 20)


def prazos(repositorio, numero, hoje=HOJE):
    pedido = repositorio.dados_pedido(numero)
    return calcular_prazos(
        pedido.status_codigo, pedido.data_compra, pedido.previsao_entrega, hoje
    )


def test_datas_do_pedido_7(repo):
    resultado = prazos(repo, 7)

    assert resultado["arrependimento"].ate == date(2026, 2, 24)
    assert resultado["troca_preferencia"].ate == date(2026, 2, 24)
    assert resultado["defeito"].ate == date(2026, 3, 5)
    assert resultado["garantia_legal"].ate == date(2026, 5, 18)


@pytest.mark.parametrize(
    ("prazo", "ultimo_dia", "dia_seguinte"),
    [
        ("arrependimento", date(2026, 2, 24), date(2026, 2, 25)),
        ("troca_preferencia", date(2026, 2, 24), date(2026, 2, 25)),
        ("defeito", date(2026, 3, 5), date(2026, 3, 6)),
        ("garantia_legal", date(2026, 5, 18), date(2026, 5, 19)),
    ],
)
def test_ultimo_dia_esta_no_prazo(repo, prazo, ultimo_dia, dia_seguinte):
    assert prazos(repo, 7, ultimo_dia)[prazo].situacao == "no_prazo"
    assert prazos(repo, 7, dia_seguinte)[prazo].situacao == "encerrado"


def test_pedido_6_com_prazos_curtos_encerrados(repo):
    resultado = prazos(repo, 6)

    assert resultado["arrependimento"].situacao == "encerrado"
    assert resultado["arrependimento"].ate == date(2026, 2, 8)
    assert resultado["troca_preferencia"].situacao == "encerrado"
    assert resultado["defeito"].situacao == "encerrado"
    assert resultado["defeito"].ate == date(2026, 2, 17)
    assert resultado["garantia_legal"].situacao == "no_prazo"


@pytest.mark.parametrize("numero", [8, 9, 13])
def test_pedido_nao_entregue_nao_iniciou(repo, numero):
    for prazo in prazos(repo, numero).values():
        assert prazo.situacao == "nao_iniciado"
        assert prazo.ate is None


@pytest.mark.parametrize("numero", [17, 18, 19, 20])
def test_pedido_cancelado_nao_se_aplica(repo, numero):
    for prazo in prazos(repo, numero).values():
        assert prazo.situacao == "nao_se_aplica"
        assert prazo.ate is None


def test_sem_previsao_de_entrega_nao_conclui(repo_fixture):
    resultado = prazos(repo_fixture, 1)

    for nome in ("arrependimento", "troca_preferencia", "garantia_legal"):
        assert resultado[nome].situacao == "indeterminado"
        assert resultado[nome].ate is None
    assert resultado["defeito"].situacao == "no_prazo"
    assert resultado["defeito"].ate == date(2026, 3, 3)


def test_sem_data_de_compra_nao_conclui_defeito():
    resultado = calcular_prazos("delivered", None, date(2026, 2, 17), HOJE)

    assert resultado["defeito"].situacao == "indeterminado"
    assert resultado["arrependimento"].situacao == "no_prazo"


def test_status_desconhecido_nao_conclui():
    resultado = calcular_prazos(
        "extraviado", date(2026, 2, 1), date(2026, 2, 10), HOJE
    )
    assert {p.situacao for p in resultado.values()} == {"indeterminado"}


def test_prazo_atravessa_a_virada_de_ano():
    resultado = calcular_prazos(
        "delivered", date(2025, 12, 20), date(2025, 12, 28), date(2026, 1, 4)
    )
    assert resultado["arrependimento"].ate == date(2026, 1, 4)
    assert resultado["arrependimento"].situacao == "no_prazo"
    assert resultado["defeito"].ate == date(2026, 1, 19)


def test_bases_dos_prazos():
    resultado = calcular_prazos("delivered", date(2026, 2, 1), date(2026, 2, 5), HOJE)

    assert resultado["defeito"].base == "data_compra"
    assert resultado["arrependimento"].base == "previsao_entrega"
    assert resultado["troca_preferencia"].base == "previsao_entrega"
    assert resultado["garantia_legal"].base == "previsao_entrega"
