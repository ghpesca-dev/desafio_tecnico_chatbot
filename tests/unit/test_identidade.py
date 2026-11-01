import pytest

from emporio.rules import contato_confere

EMAIL = "anacarol.ferreira@coldmail.com"
TELEFONE = "(67) 99654-7821"


@pytest.mark.parametrize(
    "informado",
    [
        "anacarol.ferreira@coldmail.com",
        "ANACAROL.FERREIRA@COLDMAIL.COM",
        "  anacarol.ferreira@coldmail.com ",
        "(67) 99654-7821",
        "67996547821",
        "5567996547821",
        "+55 67 99654-7821",
        "99654-7821",
        "9654-7821",
    ],
)
def test_contato_igual_e_aceito(informado):
    assert contato_confere(informado, EMAIL, TELEFONE)


@pytest.mark.parametrize(
    "informado",
    [
        "",
        "   ",
        "outra@coldmail.com",
        "anacarol.ferreira@coldmail.com.br",
        "ferreira@coldmail.com",
        "coldmail.com",
        "654-7821",  # menos de 8 dígitos
        "7821",
        "(67) 99654-7820",
        "(11) 99654-7821",
        "abc",
    ],
)
def test_contato_diferente_e_recusado(informado):
    assert not contato_confere(informado, EMAIL, TELEFONE)


def test_cadastro_vazio_nao_confere_com_nada():
    assert not contato_confere("", "", "")
    assert not contato_confere("99654-7821", "", "")


def test_email_repetido_so_abre_pedido_do_dono(repo, dados):
    clientes = dados.clientes[dados.clientes["email"] == "bruno.martins@jmail.com"]
    assert len(clientes) == 2
    ids = set(clientes["customer_id"])

    for linha in dados.pedidos.itertuples(index=False):
        esperado = linha.customer_id in ids
        assert (
            repo.pedido_confere(linha.order_id, "bruno.martins@jmail.com") is esperado
        )
