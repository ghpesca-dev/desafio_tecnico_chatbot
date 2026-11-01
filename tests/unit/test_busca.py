import json
from datetime import date

import pytest

from emporio.session import SessionState
from emporio.tools import REGISTRO, Contexto


@pytest.fixture
def buscar(repo):
    def _buscar(**args):
        contexto = Contexto(repo, SessionState(), date(2026, 2, 20))
        return json.loads(
            REGISTRO.despachar("buscar_produtos", json.dumps(args), contexto)
        )

    return _buscar


def ids(resultado):
    return [p["id"] for p in resultado["produtos"]]


def test_violoes_ate_1000(buscar, repo):
    resultado = buscar(categoria="violões", preco_max=1000)

    assert resultado["total_encontrado"] == 12
    assert resultado["exibidos"] == 10
    assert resultado["categoria_resolvida"] == "Violões"
    assert 96 not in ids(resultado)  # sem estoque
    assert 113 not in ids(resultado)  # descontinuado
    for item in ids(resultado):
        produto = repo.produto(item)
        assert produto.categoria == "Violões"
        assert produto.situacao == "disponivel"
        assert produto.preco_atual <= 1000


def test_ordena_por_menor_preco(buscar, repo):
    resultado = buscar(categoria="violões")
    precos = [repo.produto(i).preco_atual for i in ids(resultado)]
    assert precos == sorted(precos)


@pytest.mark.parametrize(
    "termo", ["violao", "Violões", "violoes", "VIOLÃO", "violão"]
)
def test_resolve_categoria_sem_acento_e_no_singular(buscar, termo):
    assert buscar(categoria=termo)["categoria_resolvida"] == "Violões"


@pytest.mark.parametrize(
    ("termo", "esperado"),
    [
        ("guitarra", "Guitarras"),
        ("baixo", "Baixos"),
        ("bateria", "Baterias e Percussão"),
        ("piano", "Teclados e Pianos"),
        ("teclado", "Teclados e Pianos"),
        ("ukulele", "Ukuleles"),
        ("guitara", "Guitarras"),
    ],
)
def test_resolve_outras_categorias(buscar, termo, esperado):
    assert buscar(categoria=termo)["categoria_resolvida"] == esperado


def test_filtro_usa_preco_atual_com_promocao(buscar):
    # Produto 121: tabela R$ 549,00, atual R$ 439,20.
    assert 121 in ids(buscar(categoria="ukulele", preco_max=450))
    # Produto 127: tabela R$ 359,00, atual R$ 323,10.
    assert 127 in ids(buscar(categoria="ukulele", preco_max=330))


def test_preco_com_pix_nao_conta_para_a_faixa(buscar):
    # Produto 95: R$ 2.199,00; no PIX, R$ 2.089,05.
    assert 95 not in ids(buscar(categoria="violão", preco_max=2100))


def test_preco_minimo(buscar, repo):
    resultado = buscar(categoria="guitarra", preco_min=5000)
    assert all(repo.produto(i).preco_atual >= 5000 for i in ids(resultado))


def test_promocao_mostra_original_e_percentual(buscar):
    item = next(
        p for p in buscar(categoria="ukulele")["produtos"] if p["id"] == 121
    )
    assert item["preco_atual"] == "R$ 439,20"
    assert item["preco_original"] == "R$ 549,00"
    assert item["desconto_percentual"] == "20%"
    assert item["promocao"] == "Desconto Exclusivo"
    assert item["preco_exibicao"] == "R$ 439,20 (de R$ 549,00, 20% de desconto)"


def test_sem_promocao_campos_nulos(buscar):
    item = next(
        p for p in buscar(categoria="violão", preco_max=1000)["produtos"]
    )
    assert item["preco_original"] is None
    assert item["desconto_percentual"] is None
    assert item["preco_exibicao"] == item["preco_atual"]


def test_nao_mostra_quantidade_em_estoque(buscar):
    bruto = json.dumps(buscar(categoria="violão"))
    assert "stock" not in bruto
    assert "estoque" not in bruto


def test_nao_lista_descontinuado_nem_em_breve(buscar):
    assert 136 not in ids(buscar(categoria="baixo"))  # descontinuado com estoque
    assert 130 not in ids(buscar(categoria="ukulele"))  # em breve com estoque


@pytest.mark.parametrize(
    "termo", ["sopro", "violino", "cordas orquestrais", "saxofone", "flauta"]
)
def test_categorias_sem_produtos(buscar, termo):
    resultado = buscar(categoria=termo)
    assert resultado["categoria_sem_itens"] is True
    assert resultado["produtos"] == []
    assert resultado["categoria_resolvida"]


def test_sopro_resolve_as_duas_categorias(buscar):
    resolvida = buscar(categoria="sopro")["categoria_resolvida"]
    assert "Madeiras" in resolvida
    assert "Metais" in resolvida


def test_categoria_desconhecida_nao_inventa(buscar):
    resultado = buscar(categoria="aeromodelo")
    assert resultado["categoria_resolvida"] is None
    assert resultado["categoria_sem_itens"] is False
    assert resultado["produtos"] == []


def test_busca_por_marca_em_texto(buscar, repo):
    resultado = buscar(texto="takamine")
    assert resultado["total_encontrado"] >= 1
    assert all("Takamine" in repo.produto(i).nome for i in ids(resultado))


def test_texto_sem_acento_e_com_erro(buscar):
    assert buscar(texto="takamine")["total_encontrado"] == buscar(
        texto="takamin"
    )["total_encontrado"]


def test_sem_filtros_retorna_disponiveis(buscar):
    resultado = buscar()
    assert resultado["exibidos"] == 10
    assert resultado["total_encontrado"] == 61  # 65 menos 96, 113, 130 e 136


def test_faixa_sem_resultado(buscar):
    resultado = buscar(categoria="violão", preco_max=1)
    assert resultado["total_encontrado"] == 0
    assert resultado["categoria_sem_itens"] is False
    assert "(67) 3341-4444" in resultado["orientacao"]


def test_preco_em_texto_e_argumento_invalido_vira_erro(buscar):
    assert "erro" in buscar(preco_max="barato")


def test_produto_incompleto_nao_aparece(repo_fixture):
    contexto = Contexto(repo_fixture, SessionState(), date(2026, 2, 20))
    resultado = json.loads(REGISTRO.despachar("buscar_produtos", "{}", contexto))
    encontrados = [p["id"] for p in resultado["produtos"]]
    assert 2 not in encontrados  # sem preço
    assert 4 not in encontrados  # categoria quebrada
