"""
Aba "Configurações" — editor visual de TODOS os valores customizáveis
de config.py, com persistência em user_config.json.

Sub-abas:
- Coordenadas (com captura assistida)
- Tempos
- Caminhos & OCR
- Tipos de Documento (tabela editável)
- Textos & Templates (despacho + assinaturas)
"""

import os
import subprocess
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QScrollArea, QGroupBox,
    QLabel, QLineEdit, QPushButton, QFileDialog, QSpinBox, QDoubleSpinBox,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QMessageBox, QFormLayout
)

import config
from gui import config_manager
from gui.coord_capture import CoordinateField, RegionField


# Agrupamento visual das coordenadas (título, lista de (chave, label))
COORD_GROUPS = [
    ("Tela principal", [
        ("COORD_BTN_INCLUIR_DOC",  "Botão Incluir Documento"),
        ("COORD_BARRA_PESQUISA",   "Barra de pesquisa de tipo"),
        ("COORD_BTN_SALVAR_FORM",  "Botão Salvar do formulário"),
        ("COORD_AREA_EDICAO",      "Centro do editor (colar)"),
    ]),
    ("Árvore do processo", [
        ("COORD_ICONE_NE_ARVORE_DMPP",  "Ícone da NE na árvore (DMPP)"),
        ("COORD_ICONE_NE_ARVORE_UFIEC", "Ícone da NE na árvore (UFIEC)"),
    ]),
    ("Formulário INTERNO", [
        ("COORD_CAMPO_DESCRICAO_INTERNO",   "Campo Descrição"),
        ("COORD_CAMPO_NOME_ARVORE_INTERNO", "Campo Nome na Árvore"),
        ("COORD_RADIO_PUBLICO",             "Radio Público"),
    ]),
    ("Formulário EXTERNO", [
        ("COORD_DROPDOWN_TIPO_EXTERNO",     "Dropdown Tipo"),
        ("COORD_CAMPO_DATA",                "Campo Data"),
        ("COORD_CAMPO_NUMERO",              "Campo Número"),
        ("COORD_CAMPO_NOME_ARVORE",         "Campo Nome na Árvore"),
        ("COORD_RADIO_NATO_DIGITAL",        "Radio Nato-digital"),
        ("COORD_RADIO_DIGITALIZADO",        "Radio Digitalizado"),
        ("COORD_DROPDOWN_TIPO_CONFERENCIA", "Dropdown Tipo de conferência"),
        ("COORD_BTN_ANEXAR_ARQUIVO",        "Botão Anexar Arquivo"),
        ("COORD_RADIO_PUBLICO_EXTERNO",     "Radio Público (externo)"),
    ]),
    ("Popups e auxiliares", [
        ("COORD_POPUP_OK_SIMILAR", "OK do popup documento similar"),
        ("COORD_REFOCO_EDITOR",    "Refocar editor ao colar link"),
    ]),
]

TEMPO_LABELS = {
    "pos_pesquisa_externo":   "Após pesquisar 'Externo'",
    "pos_salvar_form":        "Após Salvar formulário",
    "pos_salvar_editor":      "Após Ctrl+Alt+S no editor",
    "recarregar_tela":        "Entre documentos (recarregar tela)",
    "aguardar_form_carregar": "Aguardar formulário interno abrir",
    "pos_anexo_upload":       "Após upload de arquivo externo",
    "pos_click_salvar_doc04": "Delay do despacho NE",
}


class TabConfiguracoes(QWidget):
    """Editor visual de config.py com persistência em user_config.json."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dirty = False
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        self.sub_tabs = QTabWidget()
        root.addWidget(self.sub_tabs, 1)

        self.sub_tabs.addTab(self._build_tab_coordenadas(), "📍 Coordenadas")
        self.sub_tabs.addTab(self._build_tab_tempos(), "⏱ Tempos")
        self.sub_tabs.addTab(self._build_tab_caminhos(), "📂 Caminhos & OCR")
        self.sub_tabs.addTab(self._build_tab_documentos(), "📄 Tipos de Documento")
        self.sub_tabs.addTab(self._build_tab_textos(), "📝 Textos & Templates")

        # Rodapé com botões Salvar / Restaurar / Abrir JSON
        footer = QHBoxLayout()
        footer.addStretch(1)

        self.lbl_status_config = QLabel("")
        self.lbl_status_config.setStyleSheet("color: #888;")
        footer.addWidget(self.lbl_status_config)

        self.btn_abrir_json = QPushButton("📁 Abrir JSON")
        self.btn_abrir_json.clicked.connect(self._open_json)
        footer.addWidget(self.btn_abrir_json)

        self.btn_restaurar = QPushButton("↺ Restaurar padrões")
        self.btn_restaurar.clicked.connect(self._restore_defaults)
        footer.addWidget(self.btn_restaurar)

        self.btn_salvar = QPushButton("💾 Salvar")
        self.btn_salvar.setStyleSheet(
            "QPushButton { background-color: #2980b9; color: white; "
            "font-weight: bold; padding: 6px 16px; border-radius: 4px; } "
            "QPushButton:hover { background-color: #3498db; }"
        )
        self.btn_salvar.clicked.connect(self._save)
        footer.addWidget(self.btn_salvar)

        root.addLayout(footer)

    # ---------- Sub-aba Coordenadas ----------
    def _build_tab_coordenadas(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        info = QLabel(
            "💡 Dica: clique em <b>🎯 Capturar</b>, posicione o mouse sobre o alvo "
            "no SEI e aguarde 3 segundos. Use <b>👁 Ver</b> para conferir onde está.<br>"
            "Resolução base testada: <b>1600x900</b> com Firefox maximizado."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background-color: #fff3cd; padding: 8px; border-radius: 4px;")
        layout.addWidget(info)

        self.coord_fields: dict[str, CoordinateField] = {}

        for group_title, items in COORD_GROUPS:
            gb = QGroupBox(group_title)
            gv = QVBoxLayout(gb)
            for key, label in items:
                field = CoordinateField(label)
                field.value_changed.connect(self._mark_dirty)
                self.coord_fields[key] = field
                gv.addWidget(field)
            layout.addWidget(gb)

        # Região do popup (4 valores)
        gb_region = QGroupBox("Região do popup 'documento similar'")
        gvr = QVBoxLayout(gb_region)
        self.region_field = RegionField("Região do popup (x, y, largura, altura)")
        self.region_field.value_changed.connect(self._mark_dirty)
        gvr.addWidget(self.region_field)
        layout.addWidget(gb_region)

        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    # ---------- Sub-aba Tempos ----------
    def _build_tab_tempos(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        info = QLabel(
            "Aumente se o SEI estiver lento (docs não carregam a tempo). "
            "Diminua se quiser mais velocidade (por sua conta e risco)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background-color: #d1ecf1; padding: 8px; border-radius: 4px;")
        layout.addWidget(info)

        gb_globais = QGroupBox("Tempos globais")
        form_g = QFormLayout(gb_globais)

        self.spin_pause = QDoubleSpinBox()
        self.spin_pause.setRange(0.0, 10.0)
        self.spin_pause.setSingleStep(0.1)
        self.spin_pause.setDecimals(2)
        self.spin_pause.valueChanged.connect(self._mark_dirty)
        form_g.addRow("Pausa entre ações (pyautogui.PAUSE):", self.spin_pause)

        self.spin_wait = QDoubleSpinBox()
        self.spin_wait.setRange(0.0, 60.0)
        self.spin_wait.setSingleStep(0.5)
        self.spin_wait.setDecimals(2)
        self.spin_wait.valueChanged.connect(self._mark_dirty)
        form_g.addRow("Espera padrão (WAIT_FOR_ELEMENT):", self.spin_wait)

        self.spin_upload = QSpinBox()
        self.spin_upload.setRange(1, 300)
        self.spin_upload.valueChanged.connect(self._mark_dirty)
        form_g.addRow("Tempo máximo de upload (s):", self.spin_upload)

        layout.addWidget(gb_globais)

        gb_tempos = QGroupBox("Tempos específicos (dicionário TEMPOS)")
        form_t = QFormLayout(gb_tempos)

        self.tempo_spins: dict[str, QDoubleSpinBox] = {}
        for key, label in TEMPO_LABELS.items():
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 60.0)
            spin.setSingleStep(0.5)
            spin.setDecimals(2)
            spin.valueChanged.connect(self._mark_dirty)
            self.tempo_spins[key] = spin
            form_t.addRow(f"{label}:", spin)

        layout.addWidget(gb_tempos)
        layout.addStretch(1)
        scroll.setWidget(content)
        return scroll

    # ---------- Sub-aba Caminhos & OCR ----------
    def _build_tab_caminhos(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)

        gb_paths = QGroupBox("Caminhos")
        form_p = QFormLayout(gb_paths)

        # Tesseract
        h1 = QHBoxLayout()
        self.edit_tesseract = QLineEdit()
        self.edit_tesseract.textChanged.connect(self._mark_dirty)
        btn_tes = QPushButton("Procurar...")
        btn_tes.clicked.connect(self._pick_tesseract)
        h1.addWidget(self.edit_tesseract, 1)
        h1.addWidget(btn_tes)
        form_p.addRow("Tesseract OCR:", h1)

        # Documentos
        h2 = QHBoxLayout()
        self.edit_docs = QLineEdit()
        self.edit_docs.textChanged.connect(self._mark_dirty)
        btn_docs = QPushButton("Procurar...")
        btn_docs.clicked.connect(self._pick_docs_dir)
        h2.addWidget(self.edit_docs, 1)
        h2.addWidget(btn_docs)
        form_p.addRow("Pasta de documentos:", h2)

        layout.addWidget(gb_paths)

        gb_ocr = QGroupBox("OCR e Imagem")
        form_o = QFormLayout(gb_ocr)

        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["por", "eng", "spa", "por+eng"])
        self.combo_lang.setEditable(True)
        self.combo_lang.currentTextChanged.connect(self._mark_dirty)
        form_o.addRow("Idioma do Tesseract:", self.combo_lang)

        self.spin_confidence = QSpinBox()
        self.spin_confidence.setRange(0, 100)
        self.spin_confidence.valueChanged.connect(self._mark_dirty)
        form_o.addRow("Confiança mínima (%):", self.spin_confidence)

        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(72, 600)
        self.spin_dpi.setSingleStep(10)
        self.spin_dpi.valueChanged.connect(self._mark_dirty)
        form_o.addRow("DPI do PDF:", self.spin_dpi)

        self.combo_format = QComboBox()
        self.combo_format.addItems(["PNG", "JPEG", "BMP"])
        self.combo_format.currentTextChanged.connect(self._mark_dirty)
        form_o.addRow("Formato de imagem:", self.combo_format)

        layout.addWidget(gb_ocr)
        layout.addStretch(1)
        return content

    # ---------- Sub-aba Tipos de Documento ----------
    def _build_tab_documentos(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 6, 6, 6)

        info = QLabel(
            "Edite os termos de busca e campos de cada tipo de documento. "
            "⚠️ Não altere a coluna <b>chave</b> (é usada internamente no código)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background-color: #f8d7da; padding: 8px; border-radius: 4px;")
        layout.addWidget(info)

        self.tbl_docs = QTableWidget()
        self.tbl_docs.setColumnCount(6)
        self.tbl_docs.setHorizontalHeaderLabels([
            "chave", "busca", "descricao", "nome_arvore", "tipo_externo", "nome_arvore_fixo"
        ])
        self.tbl_docs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_docs.itemChanged.connect(lambda *_: self._mark_dirty())
        layout.addWidget(self.tbl_docs, 1)
        return content

    # ---------- Sub-aba Textos ----------
    def _build_tab_textos(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)

        gb_desp = QGroupBox("Template do despacho de aprovação de NE")
        gd = QVBoxLayout(gb_desp)
        info = QLabel(
            "Placeholders disponíveis: "
            "<code>{numero_ne}</code>, <code>{link_ne}</code>, <code>{data_ne}</code>"
        )
        info.setStyleSheet("color: #555;")
        gd.addWidget(info)

        self.txt_despacho = QPlainTextEdit()
        self.txt_despacho.setMinimumHeight(140)
        self.txt_despacho.textChanged.connect(self._mark_dirty)
        gd.addWidget(self.txt_despacho)
        layout.addWidget(gb_desp)

        gb_ass = QGroupBox("Assinaturas da Planilha de Pesquisa de Preço")
        ga = QVBoxLayout(gb_ass)
        info2 = QLabel(
            "O bot corta as páginas da planilha após encontrar uma destas assinaturas."
        )
        info2.setStyleSheet("color: #555;")
        ga.addWidget(info2)

        self.tbl_ass = QTableWidget()
        self.tbl_ass.setColumnCount(2)
        self.tbl_ass.setHorizontalHeaderLabels(["Nome completo (maiúsculo)", "CPF"])
        self.tbl_ass.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_ass.itemChanged.connect(lambda *_: self._mark_dirty())
        ga.addWidget(self.tbl_ass)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("➕ Adicionar")
        btn_add.clicked.connect(self._add_assinatura)
        btn_del = QPushButton("🗑 Remover selecionada")
        btn_del.clicked.connect(self._del_assinatura)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addStretch(1)
        ga.addLayout(btn_row)

        layout.addWidget(gb_ass)
        layout.addStretch(1)
        return content

    # ---------- Ações ----------
    def _pick_tesseract(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecione o executável do Tesseract",
            self.edit_tesseract.text() or "",
            "Executáveis (*.exe);;Todos (*.*)",
        )
        if path:
            self.edit_tesseract.setText(path)

    def _pick_docs_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "Selecione a pasta de documentos",
            self.edit_docs.text() or "",
        )
        if path:
            self.edit_docs.setText(path)

    def _add_assinatura(self):
        row = self.tbl_ass.rowCount()
        self.tbl_ass.insertRow(row)
        self.tbl_ass.setItem(row, 0, QTableWidgetItem(""))
        self.tbl_ass.setItem(row, 1, QTableWidgetItem(""))

    def _del_assinatura(self):
        row = self.tbl_ass.currentRow()
        if row >= 0:
            self.tbl_ass.removeRow(row)

    def _mark_dirty(self):
        self._dirty = True
        self.lbl_status_config.setText("● alterações não salvas")
        self.lbl_status_config.setStyleSheet("color: #e67e22; font-weight: bold;")

    def _mark_clean(self):
        self._dirty = False
        self.lbl_status_config.setText("✓ salvo")
        self.lbl_status_config.setStyleSheet("color: #27ae60;")

    # ---------- Load / Save ----------
    def _load_values(self):
        data = config_manager.get_current_config()

        # Coordenadas simples
        for key, field in self.coord_fields.items():
            if key in data:
                field.set_value(data[key])

        # Região
        if "REGIAO_POPUP_SIMILAR" in data:
            self.region_field.set_value(data["REGIAO_POPUP_SIMILAR"])

        # Tempos
        self.spin_pause.setValue(float(data.get("PAUSE_BETWEEN_ACTIONS", 0.5)))
        self.spin_wait.setValue(float(data.get("WAIT_FOR_ELEMENT", 1.0)))
        self.spin_upload.setValue(int(data.get("MAX_UPLOAD_WAIT", 10)))

        tempos = data.get("TEMPOS", {})
        for key, spin in self.tempo_spins.items():
            spin.setValue(float(tempos.get(key, 0.0)))

        # Caminhos & OCR
        self.edit_tesseract.setText(data.get("TESSERACT_PATH", ""))
        self.edit_docs.setText(data.get("DOCUMENTOS_DIR", ""))
        self.combo_lang.setCurrentText(data.get("OCR_LANGUAGE", "por"))
        self.spin_confidence.setValue(int(data.get("OCR_MIN_CONFIDENCE", 60)))
        self.spin_dpi.setValue(int(data.get("PDF_DPI", 200)))
        self.combo_format.setCurrentText(data.get("IMAGE_FORMAT", "PNG"))

        # Tipos de documento
        self.tbl_docs.blockSignals(True)
        docs = data.get("DOCUMENTOS", {})
        self.tbl_docs.setRowCount(len(docs))
        for row, (chave, info) in enumerate(docs.items()):
            self._set_doc_row(row, chave, info)
        self.tbl_docs.blockSignals(False)

        # Assinaturas
        self.tbl_ass.blockSignals(True)
        ass = data.get("ASSINATURAS_PLANILHA_PRECO", [])
        self.tbl_ass.setRowCount(len(ass))
        for row, item in enumerate(ass):
            nome, cpf = (item[0], item[1]) if len(item) >= 2 else ("", "")
            self.tbl_ass.setItem(row, 0, QTableWidgetItem(str(nome)))
            self.tbl_ass.setItem(row, 1, QTableWidgetItem(str(cpf)))
        self.tbl_ass.blockSignals(False)

        # Template
        self.txt_despacho.blockSignals(True)
        self.txt_despacho.setPlainText(data.get("DESPACHO_APROVACAO_TEMPLATE", ""))
        self.txt_despacho.blockSignals(False)

        if config_manager.user_config_exists():
            self.lbl_status_config.setText("✓ carregado de user_config.json")
            self.lbl_status_config.setStyleSheet("color: #27ae60;")
        else:
            self.lbl_status_config.setText("(usando defaults)")
            self.lbl_status_config.setStyleSheet("color: #888;")
        self._dirty = False

    def _set_doc_row(self, row, chave, info):
        cells = [
            chave,
            info.get("busca", ""),
            info.get("descricao", ""),
            info.get("nome_arvore", ""),
            info.get("tipo_externo", ""),
            info.get("nome_arvore_fixo", ""),
        ]
        for col, text in enumerate(cells):
            item = QTableWidgetItem(str(text))
            if col == 0:
                # Chave não-editável
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.tbl_docs.setItem(row, col, item)

    def _collect_values(self) -> dict:
        out = {}

        # Coordenadas
        for key, field in self.coord_fields.items():
            out[key] = field.get_value()
        out["REGIAO_POPUP_SIMILAR"] = self.region_field.get_value()

        # Tempos
        out["PAUSE_BETWEEN_ACTIONS"] = self.spin_pause.value()
        out["WAIT_FOR_ELEMENT"] = self.spin_wait.value()
        out["MAX_UPLOAD_WAIT"] = self.spin_upload.value()
        out["TEMPOS"] = {k: s.value() for k, s in self.tempo_spins.items()}

        # Caminhos & OCR
        out["TESSERACT_PATH"] = self.edit_tesseract.text()
        out["DOCUMENTOS_DIR"] = self.edit_docs.text()
        out["OCR_LANGUAGE"] = self.combo_lang.currentText()
        out["OCR_MIN_CONFIDENCE"] = self.spin_confidence.value()
        out["PDF_DPI"] = self.spin_dpi.value()
        out["IMAGE_FORMAT"] = self.combo_format.currentText()

        # Tipos de documento
        docs = {}
        for row in range(self.tbl_docs.rowCount()):
            chave_item = self.tbl_docs.item(row, 0)
            if not chave_item:
                continue
            chave = chave_item.text().strip()
            if not chave:
                continue
            entry = {}
            for col, key in enumerate(
                ["busca", "descricao", "nome_arvore", "tipo_externo", "nome_arvore_fixo"],
                start=1,
            ):
                it = self.tbl_docs.item(row, col)
                val = it.text().strip() if it else ""
                if val:
                    entry[key] = val
            docs[chave] = entry
        out["DOCUMENTOS"] = docs

        # Assinaturas
        ass = []
        for row in range(self.tbl_ass.rowCount()):
            nome_item = self.tbl_ass.item(row, 0)
            cpf_item = self.tbl_ass.item(row, 1)
            nome = nome_item.text().strip() if nome_item else ""
            cpf = cpf_item.text().strip() if cpf_item else ""
            if nome or cpf:
                ass.append((nome, cpf))
        out["ASSINATURAS_PLANILHA_PRECO"] = ass

        # Template
        out["DESPACHO_APROVACAO_TEMPLATE"] = self.txt_despacho.toPlainText()

        return out

    def _save(self):
        values = self._collect_values()
        try:
            config_manager.save_user_config(values)
            config_manager.load_user_config()  # re-aplica no módulo config em memória
            self._mark_clean()
            QMessageBox.information(
                self, "Configurações salvas",
                "As configurações foram salvas em user_config.json.\n\n"
                "As mudanças valem a partir da próxima execução da automação."
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro ao salvar", str(e))

    def _restore_defaults(self):
        resp = QMessageBox.question(
            self, "Restaurar padrões",
            "Isso vai apagar user_config.json e voltar a todos os valores originais "
            "de config.py. Deseja continuar?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        config_manager.reset_to_defaults()

        # Recarrega o módulo config em memória — precisa reimportar
        import importlib
        import config as _cfg
        importlib.reload(_cfg)

        self._load_values()
        QMessageBox.information(
            self, "Restaurado",
            "Valores originais restaurados. Reinicie a GUI para garantir que tudo "
            "esteja coerente."
        )

    def _open_json(self):
        path = config_manager.USER_CONFIG_PATH
        if not path.exists():
            QMessageBox.information(
                self, "Arquivo ainda não existe",
                "O user_config.json só é criado quando você salva algo pela primeira vez."
            )
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            QMessageBox.warning(self, "Erro", str(e))

    def has_unsaved_changes(self) -> bool:
        return self._dirty
