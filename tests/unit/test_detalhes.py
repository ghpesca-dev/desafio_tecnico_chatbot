import json
from datetime import date

import pytest

from emporio.session import SessionState
from emporio.tools import REGISTRO, Contexto


@pytest.fixture
def detalhes(repo):
    def _detalhes(referencia, repositorio=repo):
        contexto = Contexto(repositorio, SessionState(), date(2026, 2, 20))
        return json.loads(
            REGISTRO.despachar(
                "detalhes_produto", json.dumps({"referencia": referencia}), contexto
            )
        )

    return _detalhes


@pytest.mark.parametrize(
    "referencia",
    ["takamine gd20", "Takamine GD-20", "takamin gd20", "TAKAMINE GD 20", "95"],
)
def test_encontra_o_takamine(detalhes, referencia):
    resultado = detalhes(referencia)
    assert resultado["resultado"] == "encontrado"
    assert resultado["produto"]["id"] == 95


def test_produto_disponivel_traz_preco_e_pix(detalhes):
    resultado = detalhes("takamine gd20")
    assert resultado["produto"]["situacao"] == "disponivel"
    assert resultado["produto"]["a_venda"] is True
    assert resultado["produto"]["preco_atual"] == "R$ 2.199,00"
    assert resultado["pagamento"]["pix"] == "R$ 2.089,05"
    assert resultado["pagamento"]["pix_nao_acumula"] is False


def test_promocao_nao_acumula_com_pix(detalhes):
    resultado = detalhes("127")
    assert resultado["produto"]["preco_tabela"] == "R$ 359,00"
    assert resultado["produto"]["preco_atual"] == "R$ 323,10"
    assert resultado["produto"]["promocao_ativa"] == {
        "nome": "Oferta Especial",
        "desconto_percentual": "10%",
    }
    assert resultado["pagamento"]["pix"] == "R$ 323,10"
    assert resultado["pagamento"]["pix_nao_acumula"] is True


def test_nome_generico_e_ambiguo_com_os_candidatos(detalhes):
    resultado = detalhes("takamine")
    assert resultado["resultado"] == "ambiguo"
    assert {c["id"] for c in resultado["candidatos"]} == {95, 100, 105, 115}
    assert resultado["produto"] is None


def test_limita_candidatos_a_5(detalhes):
    assert len(detalhes("yamaha")["candidatos"]) == 5


def test_giannini_com_espaco_no_modelo(detalhes):
    resultado = detalhes("giannini gf 3d")
    assert resultado["resultado"] == "encontrado"
    assert resultado["produto"]["id"] == 96


def test_palavras_fora_de_ordem(detalhes):
    assert detalhes("natural gd20 takamine")["produto"]["id"] == 95


@pytest.mark.parametrize(
    "referencia",
    [
        "gibson sg",
        "takamine gd30",
        "takamine gd21",
        "yamaha c41",
        "martin d18",
        "taylor 314ce",
        "fender jazz bass",
    ],
)
def test_modelo_parecido_nunca_vira_outro_produto(detalhes, referencia):
    resultado = detalhes(referencia)
    assert resultado["resultado"] != "encontrado"
    assert resultado["produto"] is None
    assert resultado["pagamento"] is None


@pytest.mark.parametrize(
    "referencia",
    ["amplificador", "palheta", "pedal", "violino", "saxofone", "violao", "guitarra"],
)
def test_termo_generico_nao_encontra_produto(detalhes, referencia):
    assert detalhes(referencia)["resultado"] == "nao_encontrado"


def test_ignora_tipo_de_instrumento_na_referencia(detalhes):
    assert detalhes("violão takamine gd20")["produto"]["id"] == 95
    assert detalhes("ukulele ohana ck20")["produto"]["id"] == 121


def test_produto_inexistente(detalhes):
    resultado = detalhes("Gibson Flying V Zebrada")
    assert resultado["resultado"] == "nao_encontrado"
    assert resultado["produto"] is None
    assert resultado["alternativas"] == []
    assert "(67) 3341-4444" in resultado["orientacao"]


def test_encontrado_nao_traz_orientacao(detalhes):
    assert detalhes("95")["orientacao"] is None


def test_id_inexistente(detalhes):
    assert detalhes("99999")["resultado"] == "nao_encontrado"


def test_sem_estoque_com_alternativas(detalhes, repo):
    resultado = detalhes("giannini gf-3d")
    assert resultado["produto"]["situacao"] == "temporariamente_indisponivel"
    assert resultado["produto"]["a_venda"] is False
    assert len(resultado["alternativas"]) == 3
    for alternativa in resultado["alternativas"]:
        produto = repo.produto(alternativa["id"])
        assert produto.situacao == "disponivel"
        assert produto.categoria == "Violões"


def test_alternativas_ordenadas_por_proximidade_de_preco(detalhes, repo):
    resultado = detalhes("96")
    alvo = repo.produto(96).preco_atual
    distancias = [
        abs(repo.produto(a["id"]).preco_atual - alvo)
        for a in resultado["alternativas"]
    ]
    assert distancias == sorted(distancias)


def test_nao_sugere_o_proprio_produto(detalhes):
    resultado = detalhes("95")
    assert 95 not in [a["id"] for a in resultado["alternativas"]]


def test_produto_disponivel_tambem_tem_alternativas(detalhes):
    assert len(detalhes("95")["alternativas"]) == 3


@pytest.mark.parametrize("referencia", ["113", "136"])
def test_descontinuado(detalhes, repo, referencia):
    resultado = detalhes(referencia)
    assert resultado["produto"]["situacao"] == "fora_de_catalogo"
    assert resultado["produto"]["a_venda"] is False
    assert resultado["pagamento"] is None
    assert resultado["alternativas"]
    for alternativa in resultado["alternativas"]:
        assert repo.produto(alternativa["id"]).situacao == "disponivel"


def test_em_breve(detalhes):
    resultado = detalhes("130")
    assert resultado["produto"]["situacao"] == "em_breve"
    assert resultado["produto"]["a_venda"] is False
    assert resultado["pagamento"] is None


def test_em_breve_nunca_aparece_nas_alternativas(detalhes, repo):
    ukuleles = [p for p in repo.produtos() if p.categoria == "Ukuleles"]
    for produto in ukuleles:
        ids = [a["id"] for a in detalhes(str(produto.id))["alternativas"]]
        assert 130 not in ids


def test_nao_expoe_quantidade_em_estoque(detalhes):
    bruto = json.dumps(detalhes("95"))
    assert "stock" not in bruto
    assert "estoque" not in bruto


def test_traz_specs(detalhes):
    assert detalhes("95")["produto"]["specs"]


def test_sem_informacao_nao_preenche_preco(detalhes, repo_fixture):
    resultado = detalhes("2", repositorio=repo_fixture)
    assert resultado["produto"]["situacao"] == "sem_informacao"
    assert resultado["produto"]["preco_atual"] is None
    assert resultado["pagamento"] is None


def test_duas_promocoes_ativas_usa_a_maior(detalhes, repo_fixture):
    resultado = detalhes("1", repositorio=repo_fixture)
    assert resultado["produto"]["promocao_ativa"]["nome"] == "Promo Maior"
    assert resultado["produto"]["preco_atual"] == "R$ 750,00"


def test_referencia_vazia_e_recusada(detalhes):
    assert "erro" in detalhes("   ")
