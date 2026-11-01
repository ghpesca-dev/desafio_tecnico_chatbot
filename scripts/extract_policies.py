"""Converte o manual em PDF em um markdown por tópico. Execução única.

    uv run python scripts/extract_policies.py

O resultado fica versionado em data/processed/politicas/ e é o que o agente lê.
"""

import re
import sys
from pathlib import Path

import pdfplumber

RAIZ = Path(__file__).resolve().parents[1]
PDF = RAIZ / "data" / "políticas_da_loja.pdf"
SAIDA = RAIZ / "data" / "processed" / "politicas"

TAMANHO_RODAPE = 8.5
TAMANHO_SUBTITULO = 12
TAMANHO_TITULO = 14
FOLGA_PARAGRAFO = 7

# Seções numeradas do manual, para não confundir com a lista "1. Saudação".
SECOES = {
    1: ("loja", "Sobre a Empório da Música"),
    2: ("horario", "Horário de Funcionamento"),
    3: ("pagamento", "Formas de Pagamento"),
    4: ("trocas_devolucoes", "Política de Trocas e Devoluções"),
    5: ("frete", "Política de Frete e Entregas"),
    6: ("promocoes", "Promoções e Descontos"),
    7: ("atendimento", "Atendimento via WhatsApp"),
    8: ("garantia", "Garantia"),
    9: ("privacidade", "Privacidade e Proteção de Dados"),
    10: ("atendimento", "Disposições Finais"),
}

# O manual se contradiz nestes pontos. Cada troca segue uma decisão da spec e
# precisa acontecer: se o PDF mudar, o script falha em vez de seguir em silêncio.
SUBSTITUICOES = [
    # O telefone dos dados da empresa é o oficial (FR-006).
    ("(67) 3321-4500", "(67) 3341-4444"),
    # A capa traz o e-mail sem acento, que é o válido (FR-006).
    ("contato@empóriodamusica.com.br", "contato@emporiodamusica.com.br"),
    # O agente só responde com o catálogo fornecido, de 65 itens (FR-014).
    ("abrange mais de 300 instrumentos", "abrange instrumentos"),
    # A seção 3.1 é mais específica e prevalece sobre a tabela (FR-019).
    (
        "| Até 12x sem juros | Parcela mínima de R$ 100,00 |",
        "| Até 12x sem juros | Parcela mínima conforme a seção 3.1 |",
    ),
]

IGNORAR = ("Empório da Música — Sua música", "Última atualização:")
INICIO_ITEM = re.compile(r"^(•|\d+\. )")


def tabela_em_markdown(linhas: list[list[str]]) -> str:
    def celula(texto: str | None) -> str:
        return " ".join((texto or "").split())

    cabecalho, *corpo = [[celula(c) for c in linha] for linha in linhas]
    saida = [
        f"| {' | '.join(cabecalho)} |",
        f"|{'---|' * len(cabecalho)}",
    ]
    saida += [f"| {' | '.join(linha)} |" for linha in corpo]
    return "\n".join(saida)


def elementos_da_pagina(pagina) -> list[dict]:
    """Linhas de texto e tabelas, na ordem em que aparecem na página."""
    tabelas = pagina.find_tables()

    def fora_de_tabela(obj) -> bool:
        if obj.get("size", TAMANHO_RODAPE + 1) <= TAMANHO_RODAPE:
            return False
        centro = (obj["top"] + obj["bottom"]) / 2
        return not any(t.bbox[1] <= centro <= t.bbox[3] for t in tabelas)

    elementos = [
        {
            "tipo": "linha",
            "topo": linha["top"],
            "base": linha["bottom"],
            "texto": linha["text"].strip(),
            "tamanho": linha["chars"][0]["size"],
        }
        for linha in pagina.filter(fora_de_tabela).extract_text_lines()
    ]
    elementos += [
        {
            "tipo": "tabela",
            "topo": t.bbox[1],
            "base": t.bbox[3],
            "texto": tabela_em_markdown(t.extract()),
        }
        for t in tabelas
    ]
    return sorted(elementos, key=lambda e: e["topo"])


def titulo_de_secao(texto: str) -> int | None:
    casamento = re.fullmatch(r"(\d+)\. (.+)", texto)
    if casamento:
        numero = int(casamento[1])
        if SECOES.get(numero, (None, None))[1] == casamento[2]:
            return numero
    return None


def converter(pdf) -> dict[int, list[str]]:
    """Agrupa os blocos por seção, juntando as linhas quebradas pelo PDF."""
    secoes: dict[int, list[str]] = {}
    atual = None
    base_anterior = None

    for pagina in pdf.pages[1:]:  # A página 1 é a capa.
        for elemento in elementos_da_pagina(pagina):
            texto = elemento["texto"]
            if elemento["tipo"] == "tabela":
                secoes[atual].append(texto)
                base_anterior = None
                continue
            if texto.startswith(IGNORAR):
                continue

            numero = titulo_de_secao(texto)
            if numero:
                atual = numero
                secoes[atual] = [f"# {texto}"]
                base_anterior = None
            elif atual is None:
                continue
            elif round(elemento["tamanho"]) == TAMANHO_SUBTITULO:
                secoes[atual].append(f"## {texto}")
                base_anterior = None
            elif INICIO_ITEM.match(texto):
                secoes[atual].append(re.sub(r"^•\s*", "- ", texto))
                base_anterior = elemento["base"]
            elif (
                base_anterior is not None
                and elemento["topo"] - base_anterior < FOLGA_PARAGRAFO
            ):
                secoes[atual][-1] += f" {texto}"
                base_anterior = elemento["base"]
            else:
                secoes[atual].append(texto)
                base_anterior = elemento["base"]
    return secoes


def montar_markdown(blocos: list[str]) -> str:
    """Listas ficam sem linha em branco entre os itens; o resto, com uma."""
    saida = ""
    for bloco in blocos:
        if saida:
            lista = INICIO_ITEM_MD.match(bloco) and INICIO_ITEM_MD.match(
                saida.rsplit("\n", 1)[-1]
            )
            saida += "\n" if lista else "\n\n"
        saida += bloco
    return saida + "\n"


INICIO_ITEM_MD = re.compile(r"^(- |\d+\. )")


def aplicar_substituicoes(textos: dict[str, str]) -> dict[str, str]:
    for antigo, novo in SUBSTITUICOES:
        if not any(antigo in t for t in textos.values()):
            sys.exit(f"Substituição não aplicada, confira o PDF: {antigo!r}")
        textos = {k: t.replace(antigo, novo) for k, t in textos.items()}
    return textos


def main() -> None:
    with pdfplumber.open(PDF) as pdf:
        secoes = converter(pdf)

    faltando = set(SECOES) - set(secoes)
    if faltando:
        sys.exit(f"Seções não encontradas no PDF: {sorted(faltando)}")

    por_topico: dict[str, list[str]] = {}
    for numero in sorted(secoes):
        por_topico.setdefault(SECOES[numero][0], []).extend(secoes[numero])

    textos = aplicar_substituicoes(
        {topico: montar_markdown(blocos) for topico, blocos in por_topico.items()}
    )

    SAIDA.mkdir(parents=True, exist_ok=True)
    for topico, texto in textos.items():
        (SAIDA / f"{topico}.md").write_text(texto, encoding="utf-8")
    print(f"{len(textos)} tópicos gravados em {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
