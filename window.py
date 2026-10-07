"""
Processador de NF-e - Layout (somente tela)

pip install customtkinter pypdf
python window.py
"""

import customtkinter as ctk
from tkinter import filedialog

import app

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

COR_FUNDO = "#F3F5F9"
COR_CARD = "#FFFFFF"
COR_BORDA = "#E3E7EE"
COR_TEXTO = "#1F2937"
COR_TEXTO_SUAVE = "#6B7280"
COR_PRIMARIA = "#2563EB"
COR_PRIMARIA_HOVER = "#1D4ED8"
COR_SUCESSO = "#16A34A"
COR_SUCESSO_HOVER = "#15803D"
COR_PERIGO = "#DC2626"
COR_PERIGO_HOVER_BG = "#FEF2F2"
COR_CAMPO_LEITURA = "#EEF1F6"

FONTE = "Segoe UI"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Processador de NF-e")
        self.geometry("1020x760")
        self.minsize(900, 700)
        self.configure(fg_color=COR_FUNDO)

        self.campos_auto = {}    # campos bloqueados (dados da NF)
        self.campos_manual = {}  # campos de preenchimento manual

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        corpo = ctk.CTkScrollableFrame(self, fg_color="transparent")
        corpo.grid(row=0, column=0, sticky="nsew", padx=24, pady=(20, 0))
        corpo.grid_columnconfigure(0, weight=1)

        self._cabecalho(corpo, 0)
        self._card_selecao(corpo, 1)
        self._card_dados_auto(corpo, 2)
        self._card_manual(corpo, 3)
        self._card_exportacao(corpo, 4)
        self._barra_status()

    # ------------------------------------------------------------------
    # Componentes reutilizáveis
    # ------------------------------------------------------------------
    def _cabecalho(self, pai, linha):
        frame = ctk.CTkFrame(pai, fg_color="transparent")
        frame.grid(row=linha, column=0, sticky="ew", pady=(0, 14))
        ctk.CTkLabel(frame, text="Processador de NF-e",
                     font=(FONTE, 26, "bold"), text_color=COR_TEXTO).pack(anchor="w")
        ctk.CTkLabel(frame, text="Importe a NF-e, complete as informações e gere o arquivo.",
                     font=(FONTE, 13), text_color=COR_TEXTO_SUAVE).pack(anchor="w")

    def _card(self, pai, linha, numero, titulo, subtitulo=""):
        card = ctk.CTkFrame(pai, fg_color=COR_CARD, corner_radius=14,
                            border_width=1, border_color=COR_BORDA)
        card.grid(row=linha, column=0, sticky="ew", pady=8)
        card.grid_columnconfigure(0, weight=1)

        topo = ctk.CTkFrame(card, fg_color="transparent")
        topo.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 4))
        ctk.CTkLabel(topo, text=str(numero), width=26, height=26, corner_radius=13,
                     fg_color=COR_PRIMARIA, text_color="white",
                     font=(FONTE, 12, "bold")).pack(side="left")
        ctk.CTkLabel(topo, text=titulo, font=(FONTE, 16, "bold"),
                     text_color=COR_TEXTO).pack(side="left", padx=(10, 0))
        if subtitulo:
            ctk.CTkLabel(topo, text=subtitulo, font=(FONTE, 12),
                         text_color=COR_TEXTO_SUAVE).pack(side="left", padx=(10, 0))

        conteudo = ctk.CTkFrame(card, fg_color="transparent")
        conteudo.grid(row=1, column=0, sticky="ew", padx=20, pady=(6, 18))
        return conteudo

    def _campo(self, pai, rotulo, linha, coluna, placeholder="", somente_leitura=False):
        frame = ctk.CTkFrame(pai, fg_color="transparent")
        frame.grid(row=linha, column=coluna, sticky="ew", padx=6, pady=6)
        ctk.CTkLabel(frame, text=rotulo, font=(FONTE, 12),
                     text_color=COR_TEXTO_SUAVE, anchor="w").pack(fill="x")
        entry = ctk.CTkEntry(
            frame, height=38, corner_radius=8, border_width=1, border_color=COR_BORDA,
            fg_color=COR_CAMPO_LEITURA if somente_leitura else "white",
            text_color=COR_TEXTO, placeholder_text=placeholder, font=(FONTE, 13),
        )
        entry.pack(fill="x", pady=(3, 0))
        if somente_leitura:
            entry.configure(state="disabled")
        return entry

    # ------------------------------------------------------------------
    # Seções
    # ------------------------------------------------------------------
    def _card_selecao(self, pai, linha):
        c = self._card(pai, linha, 1, "Seleção da Nota Fiscal")
        c.grid_columnconfigure(0, weight=1)

        self.entry_arquivo = ctk.CTkEntry(
            c, height=40, corner_radius=8, border_width=1, border_color=COR_BORDA,
            fg_color="white", text_color=COR_TEXTO, font=(FONTE, 13),
            placeholder_text=r"C:\Notas\NF-e_123456.pdf",
        )
        self.entry_arquivo.grid(row=0, column=0, sticky="ew", padx=(6, 10))

        self.btn_procurar = ctk.CTkButton(
            c, text="Procurar...", height=40, width=150, corner_radius=8,
            fg_color=COR_PRIMARIA, hover_color=COR_PRIMARIA_HOVER,
            font=(FONTE, 13, "bold"), command=lambda: app.SearchNF(self),
        )
        self.btn_procurar.grid(row=0, column=1, padx=(0, 6))

    def _card_dados_auto(self, pai, linha):
        c = self._card(pai, linha, 2, "Dados carregados da NF", "preenchidos automaticamente")
        for i in range(5):
            c.grid_columnconfigure(i, weight=1, uniform="auto")

        # chaves = nomes devolvidos por extrator_nf.extrair_dados_nf
        a = self.campos_auto
        a["serie"] = self._campo(c, "Série", 0, 0, somente_leitura=True)
        a["numero_nf"] = self._campo(c, "NF", 0, 1, somente_leitura=True)
        a["destinatario"] = self._campo(c, "Destinatário", 0, 2, somente_leitura=True)
        a["cpf_cnpj_destinatario"] = self._campo(c, "CPF/CNPJ", 0, 3, somente_leitura=True)
        a["data_emissao"] = self._campo(c, "Data da emissão", 0, 4, somente_leitura=True)
        a["endereco"] = self._campo(c, "Endereço", 1, 0, somente_leitura=True)
        a["bairro_distrito"] = self._campo(c, "Bairro/Distrito", 1, 1, somente_leitura=True)
        a["municipio"] = self._campo(c, "Município", 1, 2, somente_leitura=True)
        a["uf"] = self._campo(c, "UF", 1, 3, somente_leitura=True)
        a["cep"] = self._campo(c, "CEP", 1, 4, somente_leitura=True)

    def _card_manual(self, pai, linha):
        c = self._card(pai, linha, 3, "Informações complementares", "preenchimento manual")
        for i in range(4):
            c.grid_columnconfigure(i, weight=1, uniform="manual")

        m = self.campos_manual
        m["numero_os"] = self._campo(c, "Número da OS", 0, 0, "Ex: 85505823/1")
        m["codigo_produto"] = self._campo(c, "Código do Produto", 0, 1, "Ex: 05490000-0")
        m["quantidade"] = self._campo(c, "Quantidade", 0, 2, "1")
        m["vlr_unitario"] = self._campo(c, "Vlr. Unitário", 0, 3, "0.00")

        m["descricao_produto"] = self._campo(c, "Descrição do Produto", 1, 0, "Ex: FECHADURA DIGITAL YDM60")
        m["bc_icms"] = self._campo(c, "BC ICMS", 1, 1, "0.00")
        m["vlr_icms"] = self._campo(c, "Vlr. ICMS", 1, 2, "0.00")
        m["valor_total_devolvido"] = self._campo(c, "Valor Total Devolvido", 1, 3, "0.00")

        m["vlr_total_item"] = self._campo(c, "Vlr. Total do Item", 2, 0, "0.00")
        m["vlr_ipi"] = self._campo(c, "Vlr. IPI", 2, 1, "0.00")
        

    def _card_exportacao(self, pai, linha):
        c = self._card(pai, linha, 4, "Exportação")
        c.grid_columnconfigure(0, weight=1)

        destino = ctk.CTkFrame(c, fg_color="transparent")
        destino.grid(row=0, column=0, sticky="ew", padx=6, pady=(0, 14))
        destino.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(destino, text="Pasta de destino", font=(FONTE, 12),
                     text_color=COR_TEXTO_SUAVE).grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.lbl_destino = ctk.CTkLabel(destino, text=r"C:\Processados\Devolucoes",
                                        font=(FONTE, 13), text_color=COR_TEXTO, anchor="w")
        self.lbl_destino.grid(row=0, column=1, sticky="w")
        self.btn_alterar_destino = ctk.CTkButton(
            destino, text="Alterar", width=80, height=30, corner_radius=8,
            fg_color="transparent", border_width=1, border_color=COR_BORDA,
            text_color=COR_TEXTO, hover_color=COR_CAMPO_LEITURA,
            font=(FONTE, 12), command=self.alterar_destino,
        )
        self.btn_alterar_destino.grid(row=0, column=2, padx=(12, 0))

        botoes = ctk.CTkFrame(c, fg_color="transparent")
        botoes.grid(row=1, column=0)

        self.btn_limpar = ctk.CTkButton(
            botoes, text="Limpar campos", width=200, height=46, corner_radius=10,
            fg_color="transparent", border_width=2, border_color=COR_PERIGO,
            text_color=COR_PERIGO, hover_color=COR_PERIGO_HOVER_BG,
            font=(FONTE, 14, "bold"), command=lambda: app.LimpaCampos(self),
        )
        self.btn_limpar.pack(side="left", padx=8)

        self.btn_gerar = ctk.CTkButton(
            botoes, text="Gerar Arquivo", width=240, height=46, corner_radius=10,
            fg_color=COR_SUCESSO, hover_color=COR_SUCESSO_HOVER,
            font=(FONTE, 14, "bold"), command=self.gerar_arquivo,
        )
        self.btn_gerar.pack(side="left", padx=8)

    def _barra_status(self):
        barra = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=0, height=34,
                             border_width=1, border_color=COR_BORDA)
        barra.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.lbl_status = ctk.CTkLabel(barra, text="Pronto.", font=(FONTE, 12),
                                       text_color=COR_TEXTO_SUAVE, anchor="w")
        self.lbl_status.pack(fill="x", padx=20, pady=6)

    # ------------------------------------------------------------------
    # Callbacks ainda não implementados (mover para app.py quando fizer)
    # ------------------------------------------------------------------
    def alterar_destino(self):
        # Abre a janela nativa do Windows para selecionar diretórios
        pasta_selecionada = filedialog.askdirectory(
            title="Selecione a Pasta de Destino",
            initialdir=self.lbl_destino.cget("text") # Abre na pasta que já está escrita por padrão
        )
        
        # Se o usuário escolheu uma pasta (e não cancelou a janela)
        if pasta_selecionada:
            # Atualiza o texto do rótulo na interface com o novo caminho corrigindo as barras para o padrão Windows
            caminho_windows = pasta_selecionada.replace("/", "\\")
            self.lbl_destino.configure(text=caminho_windows)

    def gerar_arquivo(self):
        pass


if __name__ == "__main__":
    App().mainloop()
