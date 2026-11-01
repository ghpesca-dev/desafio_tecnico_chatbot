import json
from datetime import date

import pytest

from emporio.session import SessionState
from emporio.tools import REGISTRO, Contexto

HOJE = date(2026, 2, 20)


def email_do_pedido(dados, numero):
    pedido = dados.pedidos[dados.pedidos["order_id"] == numero].iloc[0]
    cliente = dados.clientes[dados.clientes["customer_id"] == pedido["customer_id"]]
    return cliente.iloc[0]["email"]


@pytest.fixture
def sessao():
    return SessionState()


@pytest.fixture
def consultar(repo, sessao):
    def _consultar(numero, contato=None, escrever=True):
        args = {"numero_pedido": numero}
        if contato is not None:
            args["contato"] = contato
            if escrever:
                sessao.registrar_mensagem_cliente(f"meu contato é {contato}")
        return json.loads(
            REGISTRO.despachar(
                "consultar_pedido", json.dumps(args), Contexto(repo, sessao, HOJE)
            )
        )

    return _consultar


def test_sem_contato_nao_devolve_dados(consultar):
    resultado = consultar(8)
    assert resultado["resultado"] == "precisa_confirmacao"
    assert resultado["pedido"] is None


def test_sem_contato_nao_conta_como_falha(consultar, sessao):
    consultar(8)
    assert sessao.falhas_confirmacao == 0


def test_pedido_inexistente_sem_contato_tem_a_mesma_resposta(consultar):
    assert consultar(8) == consultar(999)


def test_contato_de_outro_cliente_e_pedido_inexistente_sao_identicos(
    consultar, dados
):
    outro = email_do_pedido(dados, 1)
    assert consultar(8, outro) == consultar(999, outro)


def test_contato_correto_devolve_o_pedido(consultar, dados):
    resultado = consultar(8, email_do_pedido(dados, 8))
    pedido = resultado["pedido"]

    assert resultado["resultado"] == "ok"
    assert pedido["numero"] == 8
    assert pedido["status"] == "enviado"
    assert pedido["rastreio"] == "BRJL5544332BR"
    assert pedido["previsao_entrega"] == "2026-02-28"
    assert pedido["data"] == "2026-02-15"
    assert pedido["pagamento"] == "cartão de débito"
    assert pedido["itens"]
    assert pedido["primeiro_nome"] == "Ana"


def test_terceira_falha_bloqueia(consultar):
    assert consultar(8, "errado@teste.com")["resultado"] == "nao_confirmado"
    assert consultar(8, "errado2@teste.com")["resultado"] == "nao_confirmado"
    assert consultar(8, "errado3@teste.com")["resultado"] == "bloqueado"


def test_bloqueado_nao_acessa_os_dados_nem_com_contato_certo(
    consultar, dados, repo, monkeypatch
):
    for i in range(3):
        consultar(8, f"errado{i}@teste.com")

    def falhar(*args):
        raise AssertionError("Dados acessados com a sessão bloqueada")

    monkeypatch.setattr(repo, "pedido_confere", falhar)
    monkeypatch.setattr(repo, "dados_pedido", falhar)

    assert consultar(8, email_do_pedido(dados, 8))["resultado"] == "bloqueado"


def test_bloqueio_mantem_pedido_ja_confirmado(consultar, dados):
    consultar(8, email_do_pedido(dados, 8))
    for i in range(3):
        consultar(1, f"errado{i}@teste.com")

    assert consultar(8)["resultado"] == "ok"
    assert consultar(1)["resultado"] == "bloqueado"


def test_confirmacao_vale_sem_repetir_o_contato(consultar, dados):
    consultar(8, email_do_pedido(dados, 8))
    assert consultar(8)["resultado"] == "ok"


def test_confirmar_um_pedido_nao_abre_outro_do_mesmo_cliente(consultar, dados):
    email = email_do_pedido(dados, 1)
    assert email == email_do_pedido(dados, 19)
    assert consultar(1, email)["resultado"] == "ok"

    assert consultar(19)["resultado"] == "precisa_confirmacao"
    # O modelo repete o contato, mas o cliente não o escreveu de novo.
    assert consultar(19, email, escrever=False)["resultado"] == "precisa_confirmacao"
    assert consultar(19, email)["resultado"] == "ok"


def test_contato_que_o_cliente_nao_escreveu_nao_vale(consultar, dados, sessao):
    resultado = consultar(8, email_do_pedido(dados, 8), escrever=False)
    assert resultado["resultado"] == "precisa_confirmacao"
    assert resultado["pedido"] is None
    assert sessao.falhas_confirmacao == 0


def test_contato_inventado_pelo_modelo_nao_conta_como_falha(consultar, sessao):
    for _ in range(5):
        assert (
            consultar(8, "inventado@teste.com", escrever=False)["resultado"]
            == "precisa_confirmacao"
        )
    assert sessao.falhas_confirmacao == 0


def test_telefone_escrito_com_outra_formatacao_vale(consultar, sessao):
    sessao.registrar_mensagem_cliente("é o (67) 99654-7821, pedido 8")
    assert consultar(8, "67996547821", escrever=False)["resultado"] == "ok"


def test_sessao_nova_nao_herda_confirmacao(consultar, repo, dados):
    consultar(8, email_do_pedido(dados, 8))
    outra = json.loads(
        REGISTRO.despachar(
            "consultar_pedido",
            json.dumps({"numero_pedido": 8}),
            Contexto(repo, SessionState(), HOJE),
        )
    )
    assert outra["resultado"] == "precisa_confirmacao"


def test_janela_de_historico_nao_zera_falhas(consultar, sessao):
    consultar(8, "errado1@teste.com")
    consultar(8, "errado2@teste.com")
    for i in range(20):
        sessao.registrar_mensagem_cliente(f"mensagem {i}")
    sessao.cortar_janela(2)

    assert sessao.falhas_confirmacao == 2
    assert consultar(8, "errado3@teste.com")["resultado"] == "bloqueado"


def test_total_registrado_prevalece(consultar, dados):
    assert consultar(3, email_do_pedido(dados, 3))["pedido"]["total"] == "R$ 3.450,00"


def test_pedido_cancelado_traz_o_motivo(consultar, dados):
    pedido = consultar(19, email_do_pedido(dados, 19))["pedido"]
    assert pedido["status"] == "cancelado"
    assert pedido["motivo_cancelamento"] == "Pagamento não confirmado dentro do prazo"


def test_pedido_nao_cancelado_nao_traz_observacoes(consultar, dados):
    assert consultar(8, email_do_pedido(dados, 8))["pedido"][
        "motivo_cancelamento"
    ] is None


def test_saida_nao_traz_dados_de_contato_nem_valor_por_item(consultar, dados):
    email = email_do_pedido(dados, 8)
    resultado = consultar(8, email)
    bruto = json.dumps(resultado, ensure_ascii=False).lower()

    assert email not in bruto
    for campo in ("email", "phone", "telefone", "customer_id", "city"):
        assert campo not in bruto
    for item in resultado["pedido"]["itens"]:
        assert set(item) == {"nome", "quantidade"}


def test_nome_completo_nao_sai_do_repositorio(consultar, dados):
    bruto = json.dumps(consultar(8, email_do_pedido(dados, 8)), ensure_ascii=False)
    pedido = dados.pedidos[dados.pedidos["order_id"] == 8].iloc[0]
    nome = dados.clientes[
        dados.clientes["customer_id"] == pedido["customer_id"]
    ].iloc[0]["name"]

    assert nome not in bruto


def test_numero_invalido_vira_erro(consultar):
    assert "erro" in consultar("abc")


def test_saida_traz_prazos(consultar, dados):
    pedido = consultar(7, email_do_pedido(dados, 7))["pedido"]

    assert pedido["prazos"]["arrependimento"] == {
        "situacao": "no_prazo",
        "ate": "2026-02-24",
        "base": "previsao_entrega",
    }
    assert pedido["prazos"]["defeito"]["base"] == "data_compra"
    assert set(pedido["prazos"]) == {
        "arrependimento",
        "troca_preferencia",
        "defeito",
        "garantia_legal",
    }
