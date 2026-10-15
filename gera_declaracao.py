"""Preenche o modelo da declaração (Word) e salva como PDF."""
import re
import shutil
import subprocess
import tempfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from docxtpl import DocxTemplate

MODELO = Path(__file__).with_name("modelo_declaracao.docx")

CAMPOS_VALOR = ("vlr_unitario", "bc_icms", "vlr_icms", "vlr_ipi",
                "vlr_total_item", "valor_total_devolvido")


class ConversaoPDFError(RuntimeError):
    """Nem o Word nem o LibreOffice conseguiram gerar o PDF."""


# ----------------------------------------------------------------------
# Formatação
# ----------------------------------------------------------------------
def para_decimal(texto: str | None) -> Decimal | None:
    """Aceita '939', '939.00', '939,00', '1.234,56' e 'R$ 1.234,56'."""
    t = re.sub(r"[^\d,.-]", "", texto or "")
    if not t:
        return None
    if "," in t:                      # formato BR: ponto = milhar, vírgula = decimal
        t = t.replace(".", "").replace(",", ".")
    try:
        return Decimal(t)
    except InvalidOperation:
        raise ValueError(f"Valor inválido: '{texto}'") from None


def formatar_moeda(valor: Decimal | None) -> str:
    """Decimal('1234.5') -> '1.234,50'."""
    return f"{valor or Decimal(0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_endereco(dados: dict[str, str | None]) -> str:
    """'Rua X, 81 - Nao consta' + bairro + município/UF -> 'Rua X, 81, Bairro, Cidade - SP'."""
    rua = re.sub(r"\s*-\s*n[aã]o consta\s*$", "", dados.get("endereco") or "", flags=re.I)
    cidade_uf = " - ".join(p for p in (dados.get("municipio"), dados.get("uf")) if p)
    return ", ".join(p for p in (rua, dados.get("bairro_distrito"), cidade_uf) if p)


# ----------------------------------------------------------------------
# Montagem e geração
# ----------------------------------------------------------------------
def montar_contexto(dados: dict[str, str | None]) -> dict[str, str]:
    """Converte os valores da tela no que vai escrito na declaração."""
    valores = {c: para_decimal(dados.get(c)) for c in CAMPOS_VALOR}

    # totais em branco são calculados
    if valores["vlr_total_item"] is None and valores["vlr_unitario"] is not None:
        qtd = para_decimal(dados.get("quantidade")) or Decimal(0)
        valores["vlr_total_item"] = qtd * valores["vlr_unitario"]
    if valores["valor_total_devolvido"] is None:
        valores["valor_total_devolvido"] = valores["vlr_total_item"]

    return {
        "data_declaracao": date.today().strftime("%d/%m/%Y"),
        "destinatario": dados.get("destinatario") or "",
        "endereco_completo": montar_endereco(dados),
        "cpf_cnpj": dados.get("cpf_cnpj_destinatario") or "",
        "numero_os": dados.get("numero_os") or "",
        "numero_nf": dados.get("numero_nf") or "",
        "serie": dados.get("serie") or "",
        "data_emissao": dados.get("data_emissao") or "",
        "codigo_produto": dados.get("codigo_produto") or "",
        "descricao_produto": dados.get("descricao_produto") or "",
        "quantidade": dados.get("quantidade") or "",
        **{c: formatar_moeda(v) for c, v in valores.items()},
    }


def _docx_para_pdf(docx: Path, pdf: Path) -> None:
    """Tenta o Word (docx2pdf) e, se não houver, o LibreOffice."""
    try:
        from docx2pdf import convert  # precisa do Microsoft Word instalado
        convert(str(docx), str(pdf))
        if pdf.exists():
            return
    except Exception:
        pass

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    for candidato in (r"C:\Program Files\LibreOffice\program\soffice.exe",
                      r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if not soffice and Path(candidato).exists():
            soffice = candidato
    if not soffice:
        raise ConversaoPDFError("Instale o Microsoft Word ou o LibreOffice para gerar o PDF.")

    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(pdf.parent), str(docx)],
        check=True, capture_output=True, timeout=120,
    )
    gerado = pdf.parent / f"{docx.stem}.pdf"
    if gerado != pdf:
        gerado.replace(pdf)


def gerar_declaracao(dados: dict[str, str | None], pasta_destino: str | Path) -> Path:
    """Preenche o modelo com `dados` e salva o PDF em `pasta_destino`.

    Returns:
        Caminho do PDF gerado.
    """
    contexto = montar_contexto(dados)
    destino = Path(pasta_destino)
    destino.mkdir(parents=True, exist_ok=True)

    nome = re.sub(r"[^\w.-]", "_", f"Declaracao_NF_{contexto['numero_nf']}_OS_{contexto['numero_os']}")
    pdf = destino / f"{nome}.pdf"

    with tempfile.TemporaryDirectory() as tmp:
        docx = Path(tmp) / f"{nome}.docx"
        modelo = DocxTemplate(MODELO)
        modelo.render(contexto, autoescape=True)  # autoescape: '&' no nome não quebra o XML
        modelo.save(docx)
        _docx_para_pdf(docx, pdf)

    return pdf
