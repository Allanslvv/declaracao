import re
from pypdf import PdfReader

NAO_ENCONTRADO = "Não encontrado"
DEBUG = False  # True para ver o texto bruto extraído do PDF

# Chave de acesso: usada só para calcular série e número (não é impressa)
REGEX_CHAVE = r"(\d{4}(?:[\s.]?\d{4}){10})"

# campos que continuam funcionando por âncora (rótulo colado ao valor)
ANCORAS = {
    "destinatario": (
        r"NOME\s*/\s*RAZ.{1,2}O SOCIAL[:\.\s]*(.+?)\s+"
        r"(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})"
    ),
    "cpf_cnpj_destinatario": (
        r"NOME\s*/\s*RAZ.{1,2}O SOCIAL[:\.\s]*.+?\s+"
        r"(\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})"
    ),
}

# Bloco de valores logo após "DESTINATÁRIO / REMETENTE":
# linha 1 = endereço + bairro + CEP | linha 2 = município + UF | depois = data de emissão
REGEX_BLOCO_DEST = re.compile(
    r"DESTINAT.RIO\s*/\s*REMETENTE[ \t]*\n"
    r"(?P<linha_end>[^\n]+)\n"
    r"(?P<linha_mun>[^\n]+)\n"
    r"(?P<data_emissao>\d{2}/\d{2}/\d{4})",
    re.IGNORECASE,
)

# Tabela de produtos: código (linha só com dígitos) + descrição (1..N linhas),
# terminando na linha numérica que começa com NCM(8) CST(3) CFOP(4) UN QTD VLR VLR
REGEX_ITEM = re.compile(
    r"^(?P<codigo>\d+)[ \t]*\n"
    r"(?P<desc>(?:[^\n]+\n)+?)"
    r"(?=\d{8}\s+\d{3}\s+\d{4}\s+[A-Z]{1,4}\s+[\d.,]+\s+[\d.,]+\s+[\d.,]+)",
    re.MULTILINE,
)


def ler_texto(caminho_pdf):
    reader = PdfReader(caminho_pdf)
    txt = "\n".join((page.extract_text() or "") for page in reader.pages)
    return txt if txt.strip() else None


def buscar(padrao, texto):
    m = re.search(padrao, texto, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else NAO_ENCONTRADO


def dados_da_chave(chave):
    """
    Estrutura da chave (44 dígitos):
    UF(2) AAMM(4) CNPJ(14) modelo(2) série(3) número(9) tpEmis(1) código(8) DV(1)
    """
    digitos = re.sub(r"\D", "", chave)
    if len(digitos) != 44:
        return {}
    numero = int(digitos[25:34])
    return {
        "serie": digitos[22:25],
        "numero_nf": f"{numero:,}".replace(",", "."),
    }


def separar_endereco_bairro(resto):

    m = re.match(
        r"^(.*?,\s*\S+(?:\s+-\s+(?:n[aã]o consta|\S+))?)\s+(.+)$",
        resto,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return resto.strip(), NAO_ENCONTRADO


def extrair_bloco_destinatario(texto):
    dados = {
        c: NAO_ENCONTRADO
        for c in ("data_emissao", "endereco", "bairro_distrito", "municipio", "uf", "cep")
    }
    m = REGEX_BLOCO_DEST.search(texto)
    if not m:
        return dados

    dados["data_emissao"] = m.group("data_emissao")

    # endereço + bairro + CEP (CEP = últimos 8 dígitos da linha)
    m_end = re.match(r"^(.+?)\s+(\d{5}-?\d{3})\s*$", m.group("linha_end").strip())
    if m_end:
        resto, cep = m_end.groups()
        cep = re.sub(r"\D", "", cep)
        dados["cep"] = f"{cep[:5]}-{cep[5:]}"
        dados["endereco"], dados["bairro_distrito"] = separar_endereco_bairro(resto)

    # município + UF (UF = 2 letras maiúsculas no fim; aceita fone depois)
    m_mun = re.match(
        r"^(.+?)\s+([A-Z]{2})(?:\s+[\d()\s.-]+)?\s*$", m.group("linha_mun").strip()
    )
    if m_mun:
        dados["municipio"], dados["uf"] = m_mun.groups()

    return dados


def extrair_produtos(texto):
    # recorta o bloco entre o último cabeçalho ("PRODUTO") e "INSCRIÇÃO MUNICIPAL"
    bloco = re.search(
        r"^PRODUTO[ \t]*\n(.*?)(?=^INSCRI..O MUNICIPAL)",
        texto,
        re.DOTALL | re.MULTILINE | re.IGNORECASE,
    )
    if not bloco:
        return NAO_ENCONTRADO

    itens = []
    for m in REGEX_ITEM.finditer(bloco.group(1)):
        linhas = [l.strip() for l in m.group("desc").strip().split("\n") if l.strip()]
        # última linha só com um token tipo SKU/referência (ex.: PTKMWG60RD) -> descarta
        if len(linhas) > 1 and re.fullmatch(r"[A-Z0-9._/-]+", linhas[-1]) and re.search(r"\d", linhas[-1]):
            linhas = linhas[:-1]
        descricao = re.sub(r"\s+", " ", " ".join(linhas))
        itens.append(f"{m.group('codigo')} - {descricao}")

    return itens if itens else NAO_ENCONTRADO


def ler_pdf(caminho_pdf):
    texto = ler_texto(caminho_pdf)
    if texto is None:
        print("O PDF não contém texto extraível.")
        return None

    if DEBUG:
        print(repr(texto[:3000]))

    # série e número (a chave em si não vai para a saída)
    chave = buscar(REGEX_CHAVE, texto)
    da_chave = dados_da_chave(chave) if chave != NAO_ENCONTRADO else {}

    dados = {
        "serie": da_chave.get("serie", NAO_ENCONTRADO),
        "numero_nf": da_chave.get("numero_nf", NAO_ENCONTRADO),
    }

    for campo, padrao in ANCORAS.items():
        dados[campo] = buscar(padrao, texto)

    dest = extrair_bloco_destinatario(texto)
    for campo in ("data_emissao", "endereco", "bairro_distrito", "municipio", "uf", "cep"):
        dados[campo] = dest[campo]


    return dados


if __name__ == "__main__":
    dados = ler_pdf(r"venv\invoice-2000018623441668.pdf")
    if dados:
        for campo, valor in dados.items():
            if campo == "descricao_produtos" and isinstance(valor, list):
                print("descricao_produtos:")
                for i, item in enumerate(valor, 1):
                    print(f"  {i}. {item}")
            else:
                print(f"{campo}: {valor}")
