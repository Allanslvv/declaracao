from tkinter import filedialog


# logica para o botao limpar
def LimpaCampos(app):
    # caminho do NF
    app.entry_arquivo.delete(0, "end")

    # campos bloqueados: precisam ser liberados antes de apagar
    for entry in app.campos_auto.values():
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.configure(state="disabled")

    # campos manuais
    for entry in app.campos_manual.values():
        entry.delete(0, "end")


# abre o explorer para selecionar o arquivo 
def SearchNF(app):
    file_path = filedialog.askopenfilename(
        initialdir="/",  
        title="Selecione o arquivo XML",
        filetypes=(("Arquivos XML", "*.xml"), ("Todos os arquivos", "*.*"))
    )

    if file_path:
        app.entry_arquivo.delete(0, "end")
        app.entry_arquivo.insert(0, file_path)
