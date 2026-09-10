"""
Aba "Configurações" — editor visual de TODOS os valores customizáveis
de config.py, com persistência em user_config.json.

Sub-abas:
- Coordenadas (com captura assistida)
- Tempos
- Caminhos & OCR
- Pipeline de Documentos (arrastar para reordenar, ativar/desativar,
  adicionar/remover/editar tipos — ver pipeline.py)
- Textos & Templates (assinaturas da planilha de preço)
"""

import os
import subprocess
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QScrollArea, QGroupBox,
    QLabel, QLineEdit, QPushButton, QFileDialog, QSpinBox, QDoubleSpinBox,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QMessageBox, QFormLayout, QAbstractItemView
)

import config
import pipeline
from gui import config_manager
from gui.coord_capture import CoordinateField, RegionField
from gui.dialog_editar_passo import DialogEditarPasso


# Agrupamento visual das coordenadas (título, lista de (chave, label))
COORD_GROUPS = [
    ("Tela principal", [
        ("COORD_BTN_INCLUIR_DOC",  "Botão Incluir Documento"),
        ("COORD_BARRA_PESQUISA",   "Barra de pesquisa de tipo"),
        ("COORD_BTN_SALVAR_FORM",  "Botão Salvar do formulário"),
        ("COORD_AREA_EDICAO",      "Centro do editor (colar)"),
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
# NOTA: as coordenadas dos ícones de despachos gerados na árvore (ex:
# despacho de aprovação de NE) NÃO ficam aqui — elas vivem dentro do
# próprio passo do pipeline (aba "Pipeline de Documentos"), porque
# cada despacho gerado tem sua própria coordenada por tipo de processo.

TEMPO_LABELS = {
    "pos_pesquisa_externo":   "Após pesquisar 'Externo'",
    "pos_salvar_form":        "Após Salvar formulário",
    "pos_salvar_editor":      "Após Ctrl+Alt+S no editor",
    "recarregar_tela":        "Entre documentos (recarregar tela)",
    "aguardar_form_carregar": "Aguardar formulário interno abrir",
    "pos_anexo_upload":       "Após upload de arquivo externo",
    "pos_click_salvar_doc04": "Delay pós-salvar de despachos gerados",
}

CATEGORIA_LABEL = {
    "fixo_inicial": "Fixo (início)",
    "ciclo": "Ciclo (por Nota Fiscal)",
    "fixo_final": "Fixo (fim)",
}


class TabConfiguracoes(QWidget):
    """Editor visual de config.py + pipeline.py, com persistência em disco."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dirty = False
        self._passos = []  # lista de dicts do pipeline em edição
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
        self.sub_tabs.addTab(self._build_tab_pipeline(), "🧩 Pipeline de Documentos")
        self.sub_tabs.addTab(self._build_tab_textos(), "📝 Textos & Templates")

        footer = QHBoxLayout()
        footer.addStretch(1)

        self.lbl_status_config = QLabel("")
        self.lbl_status_config.setStyleSheet("color: #888;")
        footer.addWidget(self.lbl_status_config)

        self.btn_abrir_json = QPushButton("📁 Abrir pasta de configs")
        self.btn_abrir_json.clicked.connect(self._open_config_folder)
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

        h1 = QHBoxLayout()
        self.edit_tesseract = QLineEdit()
        self.edit_tesseract.textChanged.connect(self._mark_dirty)
        btn_tes = QPushButton("Procurar...")
        btn_tes.clicked.connect(self._pick_tesseract)
        h1.addWidget(self.edit_tesseract, 1)
        h1.addWidget(btn_tes)
        form_p.addRow("Tesseract OCR:", h1)

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

    # ---------- Sub-aba Pipeline de Documentos ----------
    def _build_tab_pipeline(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 6, 6, 6)

        info = QLabel(
            "Cada linha é um tipo de documento. Arraste para reordenar a "
            "execução DENTRO de cada seção. Desmarque 'Ativo' para pular um "
            "tipo sem apagar a configuração. Passos com 🔒 têm lógica própria "
            "de extração de dados e não podem ser removidos, só desativados."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background-color: #f8d7da; padding: 8px; border-radius: 4px;")
        layout.addWidget(info)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("➕ Novo tipo de documento")
        btn_add.clicked.connect(self._adicionar_passo)
        btn_row.addWidget(btn_add)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.tabelas_pipeline: dict[str, QTableWidget] = {}
        for categoria, label in CATEGORIA_LABEL.items():
            gb = QGroupBox(label)
            gv = QVBoxLayout(gb)
            tbl = QTableWidget()
            tbl.setColumnCount(5)
            tbl.setHorizontalHeaderLabels(["Ativo", "Id", "Origem", "Aplica-se a", ""])
            tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            tbl.verticalHeader().setVisible(False)
            tbl.setSelectionBehavior(QTableWidget.SelectRows)
            tbl.setDragDropMode(QAbstractItemView.InternalMove)
            tbl.setDragDropOverwriteMode(False)
            tbl.setDropIndicatorShown(True)
            tbl.setEditTriggers(QTableWidget.NoEditTriggers)
            tbl.model().rowsMoved.connect(lambda *_, cat=categoria: self._reordenar_apos_drag(cat))
            tbl.cellDoubleClicked.connect(lambda r, c, cat=categoria: self._editar_passo(cat, r))
            self.tabelas_pipeline[categoria] = tbl
            gv.addWidget(tbl)
            layout.addWidget(gb)

        return content

    def _passos_da_categoria(self, categoria):
        return sorted(
            [p for p in self._passos if p["categoria"] == categoria],
            key=lambda p: p.get("ordem", 0),
        )

    def _repovoar_tabelas_pipeline(self):
        for categoria, tbl in self.tabelas_pipeline.items():
            tbl.blockSignals(True)
            passos = self._passos_da_categoria(categoria)
            tbl.setRowCount(len(passos))
            for row, p in enumerate(passos):
                self._preencher_linha_pipeline(tbl, row, p)
            tbl.blockSignals(False)

    def _preencher_linha_pipeline(self, tbl, row, p):
        from PySide6.QtWidgets import QCheckBox

        chk = QCheckBox()
        chk.setChecked(p.get("ativo", True))
        chk.toggled.connect(lambda val, pid=p["id"]: self._toggle_ativo(pid, val))
        cell_wrap = QWidget()
        cw_layout = QHBoxLayout(cell_wrap)
        cw_layout.setContentsMargins(0, 0, 0, 0)
        cw_layout.addWidget(chk)
        cw_layout.addStretch(1)
        tbl.setCellWidget(row, 0, cell_wrap)

        prefixo = "🔒 " if p.get("processor") not in (
            None, "generico_imagem_pdf", "generico_upload_externo", "despacho_gerado"
        ) else ""
        ancora = " ⚓" if p.get("ancora_ciclo") else ""
        item_id = QTableWidgetItem(f"{prefixo}{p['id']}{ancora}")
        item_id.setData(Qt.UserRole, p["id"])
        tbl.setItem(row, 1, item_id)

        origem_label = "Gerado" if p.get("origem") == "gerado" else ("Interno" if p.get("modo") == "interno" else "Externo")
        tbl.setItem(row, 2, QTableWidgetItem(origem_label))

        aplica = "/".join(p.get("aplica_a", []))
        tbl.setItem(row, 3, QTableWidgetItem(aplica))

        btn_remover = QPushButton("🗑")
        btn_remover.setToolTip("Remover este tipo de documento")
        removivel = p.get("processor") in (None, "generico_imagem_pdf", "generico_upload_externo", "despacho_gerado")
        btn_remover.setEnabled(removivel)
        btn_remover.clicked.connect(lambda _, pid=p["id"]: self._remover_passo(pid))
        tbl.setCellWidget(row, 4, btn_remover)

    def _toggle_ativo(self, passo_id, valor):
        for p in self._passos:
            if p["id"] == passo_id:
                p["ativo"] = valor
        self._mark_dirty()

    def _reordenar_apos_drag(self, categoria):
        tbl = self.tabelas_pipeline[categoria]
        novos_ids_em_ordem = []
        for row in range(tbl.rowCount()):
            item = tbl.item(row, 1)
            if item:
                novos_ids_em_ordem.append(item.data(Qt.UserRole))

        passo_por_id = {p["id"]: p for p in self._passos}
        for nova_ordem, pid in enumerate(novos_ids_em_ordem, start=1):
            if pid in passo_por_id:
                passo_por_id[pid]["ordem"] = nova_ordem * 10

        self._mark_dirty()
        self._repovoar_tabelas_pipeline()

    def _adicionar_passo(self):
        dlg = DialogEditarPasso(passo=None, passos_existentes=self._passos, parent=self)
        if dlg.exec():
            self._passos.append(dlg.passo)
            self._mark_dirty()
            self._repovoar_tabelas_pipeline()

    def _editar_passo(self, categoria, row):
        passos = self._passos_da_categoria(categoria)
        if row >= len(passos):
            return
        passo = passos[row]
        dlg = DialogEditarPasso(passo=passo, passos_existentes=self._passos, parent=self)
        if dlg.exec():
            for i, p in enumerate(self._passos):
                if p["id"] == passo["id"]:
                    self._passos[i] = dlg.passo
                    break
            self._mark_dirty()
            self._repovoar_tabelas_pipeline()

    def _remover_passo(self, passo_id):
        passo = next((p for p in self._passos if p["id"] == passo_id), None)
        if not passo:
            return
        resp = QMessageBox.question(
            self, "Remover tipo de documento",
            f"Remover o passo '{passo_id}' do pipeline? Isso não afeta arquivos já "
            "existentes na pasta — só faz o bot parar de procurar por esse tipo.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        self._passos = [p for p in self._passos if p["id"] != passo_id]
        self._mark_dirty()
        self._repovoar_tabelas_pipeline()

    # ---------- Sub-aba Textos ----------
    def _build_tab_textos(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)

        info = QLabel(
            "O template do despacho de aprovação de NE e de qualquer outro "
            "documento 'gerado pelo bot' agora são editados na aba <b>🧩 Pipeline "
            "de Documentos</b> (dê duplo clique no passo)."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background-color: #d1ecf1; padding: 8px; border-radius: 4px;")
        layout.addWidget(info)

        gb_ass = QGroupBox("Assinaturas da Planilha de Pesquisa de Preço")
        ga = QVBoxLayout(gb_ass)
        info2 = QLabel(
            "O bot corta as páginas do Quadro Comparativo após encontrar uma "
            "destas assinaturas. Vale para o passo 'quadro_comparativo' do pipeline."
        )
        info2.setWordWrap(True)
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

        for key, field in self.coord_fields.items():
            if key in data:
                field.set_value(data[key])

        if "REGIAO_POPUP_SIMILAR" in data:
            self.region_field.set_value(data["REGIAO_POPUP_SIMILAR"])

        self.spin_pause.setValue(float(data.get("PAUSE_BETWEEN_ACTIONS", 0.5)))
        self.spin_wait.setValue(float(data.get("WAIT_FOR_ELEMENT", 1.0)))
        self.spin_upload.setValue(int(data.get("MAX_UPLOAD_WAIT", 10)))

        tempos = data.get("TEMPOS", {})
        for key, spin in self.tempo_spins.items():
            spin.setValue(float(tempos.get(key, 0.0)))

        self.edit_tesseract.setText(data.get("TESSERACT_PATH", ""))
        self.edit_docs.setText(data.get("DOCUMENTOS_DIR", ""))
        self.combo_lang.setCurrentText(data.get("OCR_LANGUAGE", "por"))
        self.spin_confidence.setValue(int(data.get("OCR_MIN_CONFIDENCE", 60)))
        self.spin_dpi.setValue(int(data.get("PDF_DPI", 200)))
        self.combo_format.setCurrentText(data.get("IMAGE_FORMAT", "PNG"))

        # Pipeline
        self._passos = [dict(p) for p in pipeline.carregar_pipeline(config.BASE_DIR)]
        self._repovoar_tabelas_pipeline()

        # Assinaturas (vivem dentro do passo 'quadro_comparativo')
        quadro = next((p for p in self._passos if p["id"] == "quadro_comparativo"), None)
        ass = ((quadro or {}).get("processor_config") or {}).get("assinaturas", [])
        self.tbl_ass.blockSignals(True)
        self.tbl_ass.setRowCount(len(ass))
        for row, item in enumerate(ass):
            nome, cpf = (item[0], item[1]) if len(item) >= 2 else ("", "")
            self.tbl_ass.setItem(row, 0, QTableWidgetItem(str(nome)))
            self.tbl_ass.setItem(row, 1, QTableWidgetItem(str(cpf)))
        self.tbl_ass.blockSignals(False)

        if config_manager.user_config_exists() or pipeline.pipeline_customizado(config.BASE_DIR):
            self.lbl_status_config.setText("✓ configuração carregada")
            self.lbl_status_config.setStyleSheet("color: #27ae60;")
        else:
            self.lbl_status_config.setText("(usando defaults)")
            self.lbl_status_config.setStyleSheet("color: #888;")
        self._dirty = False

    def _collect_values(self) -> dict:
        out = {}

        for key, field in self.coord_fields.items():
            out[key] = field.get_value()
        out["REGIAO_POPUP_SIMILAR"] = self.region_field.get_value()

        out["PAUSE_BETWEEN_ACTIONS"] = self.spin_pause.value()
        out["WAIT_FOR_ELEMENT"] = self.spin_wait.value()
        out["MAX_UPLOAD_WAIT"] = self.spin_upload.value()
        out["TEMPOS"] = {k: s.value() for k, s in self.tempo_spins.items()}

        out["TESSERACT_PATH"] = self.edit_tesseract.text()
        out["DOCUMENTOS_DIR"] = self.edit_docs.text()
        out["OCR_LANGUAGE"] = self.combo_lang.currentText()
        out["OCR_MIN_CONFIDENCE"] = self.spin_confidence.value()
        out["PDF_DPI"] = self.spin_dpi.value()
        out["IMAGE_FORMAT"] = self.combo_format.currentText()

        return out

    def _coletar_assinaturas(self):
        ass = []
        for row in range(self.tbl_ass.rowCount()):
            nome_item = self.tbl_ass.item(row, 0)
            cpf_item = self.tbl_ass.item(row, 1)
            nome = nome_item.text().strip() if nome_item else ""
            cpf = cpf_item.text().strip() if cpf_item else ""
            if nome or cpf:
                ass.append([nome, cpf])
        return ass

    def _save(self):
        values = self._collect_values()
        try:
            config_manager.save_user_config(values)
            config_manager.load_user_config()

            # Assinaturas voltam pro passo 'quadro_comparativo' antes de salvar o pipeline
            ass = self._coletar_assinaturas()
            for p in self._passos:
                if p["id"] == "quadro_comparativo":
                    p.setdefault("processor_config", {})["assinaturas"] = ass

            erros = pipeline.validar_pipeline(self._passos)
            if erros:
                QMessageBox.warning(self, "Pipeline inválido", "\n".join(erros))
                return
            pipeline.salvar_pipeline(config.BASE_DIR, self._passos)

            self._mark_clean()
            QMessageBox.information(
                self, "Configurações salvas",
                "As configurações e o pipeline foram salvos.\n\n"
                "As mudanças valem a partir da próxima execução da automação."
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro ao salvar", str(e))

    def _restore_defaults(self):
        resp = QMessageBox.question(
            self, "Restaurar padrões",
            "Isso apaga user_config.json e pipeline_config.json, voltando a todos "
            "os valores e tipos de documento originais. Deseja continuar?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        config_manager.reset_to_defaults()
        pipeline.restaurar_pipeline_padrao(config.BASE_DIR)

        import importlib
        import config as _cfg
        importlib.reload(_cfg)

        self._load_values()
        QMessageBox.information(
            self, "Restaurado",
            "Valores originais restaurados. Reinicie a GUI para garantir que tudo "
            "esteja coerente."
        )

    def _open_config_folder(self):
        path = config_manager.USER_CONFIG_PATH.parent
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            QMessageBox.warning(self, "Erro", str(e))

    def has_unsaved_changes(self) -> bool:
        return self._dirty
