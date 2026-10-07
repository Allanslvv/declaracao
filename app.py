"""Ações da tela: conecta os botões ao extrator de NF."""
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from extrator_nf import NFSemTextoError, extrair_dados_nf

if TYPE_CHECKING:  # só para type hint; evita import circular em runtime
    from window import App


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
