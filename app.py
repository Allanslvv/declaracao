"""Ações da tela: conecta os botões ao extrator de NF e ao gerador da declaração."""
import os
import sys
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from extrator_nf import NFSemTextoError, extrair_dados_nf
from gera_declaracao import gerar_declaracao

if TYPE_CHECKING:  # só para type hint; evita import circular em runtime
    from janela import App

# campos sem os quais a declaração não faz sentido
OBRIGATORIOS = {
    "destinatario": "Destinatário (carregue a NF)",
    "numero_nf": "Número da NF (carregue a NF)",
    "numero_os": "Número da OS",
    "codigo_produto": "Código do Produto",
    "descricao_produto": "Descrição do Produto",
    "quantidade": "Quantidade",
    "vlr_unitario": "Vlr. Unitário",
}


def preencher(entry: ctk.CTkEntry, valor: str | None) -> None:
    """Escreve no Entry mesmo se ele estiver desabilitado."""
    estado = entry.cget("state")
    entry.configure(state="normal")
    entry.delete(0, "end")
    if valor:  # insert("") apagaria o placeholder
        entry.insert(0, valor)
    entry.configure(state=estado)


def SearchNF(janela: "App") -> None:
    """Abre o seletor, extrai os dados do PDF e preenche o card 2."""
    caminho = filedialog.askopenfilename(
        title="Selecione a NF-e", filetypes=[("DANFE (PDF)", "*.pdf")]
    )
    if not caminho:  # usuário cancelou
        return

    preencher(janela.entry_arquivo, caminho)
    janela.lbl_status.configure(text="Lendo NF...")
    janela.update_idletasks()

    try:
        dados = extrair_dados_nf(caminho)
    except NFSemTextoError as e:
        messagebox.showwarning("PDF sem texto", str(e))
        janela.lbl_status.configure(text="Falha ao ler a NF.")
        return
    except Exception as e:  # PDF corrompido, sem permissão etc.
        messagebox.showerror("Erro ao ler NF", str(e))
        janela.lbl_status.configure(text="Falha ao ler a NF.")
        return

    # chaves de campos_auto = chaves devolvidas pelo extrator
    for campo, entry in janela.campos_auto.items():
        preencher(entry, dados.get(campo))

    faltando = [campo for campo in janela.campos_auto if not dados.get(campo)]
    janela.lbl_status.configure(
        text=f"NF carregada. Sem dados para: {', '.join(faltando)}" if faltando else "NF carregada."
    )


def LimpaCampos(janela: "App") -> None:
    """Zera arquivo selecionado, dados da NF e campos manuais."""
    for entry in (janela.entry_arquivo, *janela.campos_auto.values(), *janela.campos_manual.values()):
        preencher(entry, None)
    janela.lbl_status.configure(text="Pronto.")


def alterar_destino(janela: "App") -> None:
    """Escolhe a pasta onde o PDF da declaração será salvo."""
    pasta = filedialog.askdirectory(title="Pasta de destino", initialdir=janela.lbl_destino.cget("text"))
    if pasta:
        janela.lbl_destino.configure(text=os.path.normpath(pasta))


def ler_campos(janela: "App") -> dict[str, str]:
    """Junta o que está nos cards 2 e 3 num único dicionário."""
    return {
        campo: entry.get().strip()
        for campo, entry in (janela.campos_auto | janela.campos_manual).items()
    }


def gerar_arquivo(janela: "App") -> None:
    """Valida os campos, gera a declaração em PDF e oferece abrir."""
    dados = ler_campos(janela)

    faltando = [rotulo for campo, rotulo in OBRIGATORIOS.items() if not dados.get(campo)]
    if faltando:
        messagebox.showwarning("Campos obrigatórios", "Preencha:\n- " + "\n- ".join(faltando))
        return

    janela.lbl_status.configure(text="Gerando declaração...")
    janela.update_idletasks()

    try:
        pdf = gerar_declaracao(dados, janela.lbl_destino.cget("text"))
    except ValueError as e:  # valor digitado inválido (ex.: '12,3,4')
        messagebox.showwarning("Valor inválido", str(e))
        janela.lbl_status.configure(text="Corrija os valores e tente novamente.")
        return
    except Exception as e:  # sem Word/LibreOffice, pasta sem permissão, PDF aberto etc.
        messagebox.showerror("Erro ao gerar", str(e))
        janela.lbl_status.configure(text="Falha ao gerar a declaração.")
        return

    janela.lbl_status.configure(text=f"Declaração gerada: {pdf}")
    if messagebox.askyesno("Declaração gerada", f"Arquivo salvo em:\n{pdf}\n\nDeseja abrir agora?"):
        if sys.platform == "win32":
            os.startfile(pdf)
