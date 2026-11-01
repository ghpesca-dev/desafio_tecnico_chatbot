"""SC-005: pelo menos 90% das variações levam ao produto certo ou a uma confirmação."""

VARIACOES = [
    ("takamine gd20", 95),
    ("takamine gd 20", 95),
    ("takamene gd20", 95),
    ("yamaha c 40", 81),
    ("yamaha c-40", 81),
    ("yamaha f310", 87),
    ("yamha f310", 87),
    ("fender stratocaster", 145),
    ("fender strato caster", 145),
    ("fendr stratocaster", 145),
    ("stratocaster", 145),
    ("telecaster", 134),
    ("gibson les paul", 131),
    ("les paul", 131),
    ("gibson lespaul", 131),
    ("martin d28", 93),
    ("bateria acustica pearl", 140),
    ("bateria pearl", 140),
    ("kala ka 15s", 116),
    ("ukulele ohana ck20", 121),
]


def _acertou(repo, consulta, esperado):
    resultado = repo.buscar_referencia(consulta)
    if resultado.tipo == "encontrado":
        return resultado.produto.id == esperado
    return esperado in {p.id for p in resultado.candidatos}


def test_ao_menos_90_por_cento_das_variacoes(repo):
    assert len(VARIACOES) == 20
    erros = [
        (consulta, esperado)
        for consulta, esperado in VARIACOES
        if not _acertou(repo, consulta, esperado)
    ]
    assert len(erros) <= 2, f"Erros: {erros}"
