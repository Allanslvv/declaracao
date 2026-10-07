"""Extração de dados do DANFE (PDF) de NF-e."""
import re
from pathlib import Path

from pypdf import PdfReader


class NFSemTextoError(ValueError):
    """O PDF não possui texto extraível (ex.: nota digitalizada)."""


CPF_CNPJ = r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"

REGEX_CHAVE = re.compile(r"\d{4}(?:[\s.]?\d{4}){10}")

# "NOME / RAZÃO SOCIAL" seguido do nome e do CPF/CNPJ na mesma linha
REGEX_DESTINATARIO = re.compile(
    rf"NOME\s*/\s*RAZ.{{1,2}}O SOCIAL[:.\s]*(?P<nome>.+?)\s+(?P<doc>{CPF_CNPJ})",
    re.IGNORECASE,
)

# Bloco após "DESTINATÁRIO / REMETENTE":
# linha 1 = endereço + bairro + CEP | linha 2 = município + UF | depois = data de emissão
REGEX_BLOCO_DEST = re.compile(
    r"DESTINAT.RIO\s*/\s*REMETENTE[ \t]*\n"
    r"(?P<linha_end>[^\n]+)\n"
    r"(?P<linha_mun>[^\n]+)\n"
    r"(?P<data_emissao>\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)

# Tabela de produtos: código + descrição (1..N linhas) até a linha NCM CST CFOP UN QTD VLR VLR
REGEX_ITEM = re.compile(
    r"^(?P<codigo>\d+)[ \t]*\n"
    r"(?P<desc>(?:[^\n]+\n)+?)"
    r"(?=\d{8}\s+\d{3}\s+\d{4}\s+[A-Z]{1,4}\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+)",
    re.MULTILINE,
)


def _ler_texto(caminho: Path) -> str:
    texto = "\n".join(p.extract_text() or "" for p in PdfReader(caminho).pages)
    if not texto.strip():
        raise NFSemTextoError(f"'{caminho.name}' não contém texto extraível.")
    return texto


def _dados_da_chave(texto: str) -> dict[str, str | None]:
    """UF(2) AAMM(4) CNPJ(14) mod(2) série(3) número(9) tpEmis(1) código(8) DV(1)."""
    m = REGEX_CHAVE.search(texto)
    digitos = re.sub(r"\D", "", m[0]) if m else ""
    if len(digitos) != 44:
        return {"chave": None, "serie": None, "numero_nf": None}
    return {
        "chave": digitos,
        "serie": digitos[22:25],
        "numero_nf": f"{int(digitos[25:34]):,}".replace(",", "."),
    }


def _dados_destinatario(texto: str) -> dict[str, str | None]:
    m = REGEX_DESTINATARIO.search(texto)
    return {
        "destinatario": m["nome"].strip() if m else None,
        "cpf_cnpj_destinatario": m["doc"] if m else None,
    }


def _separar_endereco_bairro(resto: str) -> tuple[str, str | None]:
    m = re.match(
        r"^(.*?,\s*\S+(?:\s+-\s+(?:n[aã]o consta|\S+))?)\s+(.+)$", resto, re.IGNORECASE
    )
    return (m[1].strip(), m[2].strip()) if m else (resto.strip(), None)


def _bloco_destinatario(texto: str) -> dict[str, str | None]:
    dados: dict[str, str | None] = dict.fromkeys(
        ("data_emissao", "endereco", "bairro_distrito", "municipio", "uf", "cep")
    )
    if not (m := REGEX_BLOCO_DEST.search(texto)):
        return dados

    dados["data_emissao"] = m["data_emissao"]

    # endereço + bairro + CEP (CEP = 8 dígitos no fim da linha)
    if m_end := re.match(r"^(.+?)\s+(\d{5}-?\d{3})\s*$", m["linha_end"].strip()):
        resto, cep = m_end.groups()
        cep = re.sub(r"\D", "", cep)
        dados["cep"] = f"{cep[:5]}-{cep[5:]}"
        dados["endereco"], dados["bairro_distrito"] = _separar_endereco_bairro(resto)

    # município + UF (UF = 2 maiúsculas no fim; aceita telefone depois)
    if m_mun := re.match(r"^(.+?)\s+([A-Z]{2})(?:\s+[\d()\s.-]+)?\s*$", m["linha_mun"].strip()):
        dados["municipio"], dados["uf"] = m_mun.groups()

    return dados


def extrair_produtos(texto: str) -> list[str]:
    """Itens da tabela de produtos no formato 'código - descrição'."""
    bloco = re.search(
        r"^PRODUTO[ \t]*\n(.*?)(?=^INSCRI..O MUNICIPAL)",
        texto,
        re.DOTALL | re.MULTILINE | re.IGNORECASE,
    )
    if not bloco:
        return []

    itens = []
    for m in REGEX_ITEM.finditer(bloco[1]):
        linhas = [l.strip() for l in m["desc"].splitlines() if l.strip()]
        if len(linhas) > 1 and re.fullmatch(r"[A-Z0-9._/-]*\d[A-Z0-9._/-]*", linhas[-1]):
            linhas.pop()  # descarta linha de SKU/referência (ex.: PTKMWG60RD)
        itens.append(f"{m['codigo']} - {' '.join(' '.join(linhas).split())}")
    return itens


def extrair_dados_nf(caminho: str | Path) -> dict[str, str | None]:
    """Lê o DANFE e devolve só os valores; campo não encontrado = None.

    Raises:
        NFSemTextoError: PDF sem camada de texto.
        FileNotFoundError / pypdf.errors.PdfReadError: arquivo inválido.
    """
    texto = _ler_texto(Path(caminho))
    return {
        **_dados_da_chave(texto),
        **_dados_destinatario(texto),
        **_bloco_destinatario(texto),
    }


if __name__ == "__main__":  # teste rápido: python extrator_nf.py nota.pdf
    import sys

    for campo, valor in extrair_dados_nf(sys.argv[1]).items():
        print(f"{campo}: {valor}")
