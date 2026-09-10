"""
Diálogo para criar ou editar um PASSO do pipeline de documentos.

Cobre os campos essenciais de forma amigável:
- categoria (fixo inicial / ciclo / fixo final), ativo, âncora de ciclo
- a quais tipos de processo se aplica (DMPP / UFIEC)
- origem (arquivo / gerado) e, se arquivo: modo (interno/externo),
  palavras-chave de detecção, e os campos do formulário do SEI
- se gerado: template de texto, captura de link (com calibração de
  coordenada por tipo de processo) e os placeholders do template

Passos "de fábrica" (com processador específico, ex: nota_fiscal) têm
o campo 'processor' preservado sem exposição na UI — este diálogo só
lida com o que é seguro editar sem quebrar a lógica de extração.
"""

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QLineEdit, QComboBox, QCheckBox, QSpinBox, QPlainTextEdit,
    QDialogButtonBox, QMessageBox, QWidget
)

import pipeline
from gui.coord_capture import CoordinateField


class DialogEditarPasso(QDialog):
    """Se `passo` for None, cria um novo passo. Senão, edita uma cópia dele."""

    def __init__(self, passo=None, passos_existentes=None, parent=None):
        super().__init__(parent)
        self.passo_original = passo
        self.eh_novo = passo is None
        self.passos_existentes = passos_existentes or []
        self.passo = dict(passo) if passo else self._passo_em_branco()

        self.setWindowTitle("Novo tipo de documento" if self.eh_novo else f"Editar '{self.passo['id']}'")
        self.resize(560, 640)
        self._build_ui()
        self._carregar_valores()

    def _passo_em_branco(self):
        return {
            "id": "", "categoria": "ciclo", "ordem": 50,
            "origem": "arquivo", "modo": "interno", "ativo": True,
            "aplica_a": ["DMPP", "UFIEC"], "ancora_ciclo": False,
            "deteccao": {"contains_any": []},
            "processor": None,  # decidido automaticamente ao salvar
            "config_doc": {"busca": "", "descricao": "", "nome_arvore": ""},
            "gerado_config": {
                "template": "", "campos": [], "captura_link": False,
                "link_step_alvo": None, "coord_icone_arvore": {},
            },
        }

    # ---------------- UI ----------------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form_geral = QFormLayout()
        self.edit_id = QLineEdit()
        self.edit_id.setPlaceholderText("ex: despacho_validacao (sem espaços/acentos)")
        self.edit_id.setEnabled(self.eh_novo)  # id não muda depois de criado
        form_geral.addRow("Identificador interno:", self.edit_id)

        self.combo_categoria = QComboBox()
        self.combo_categoria.addItem("Fixo — no início do processo", "fixo_inicial")
        self.combo_categoria.addItem("Ciclo — repete em toda Nota Fiscal", "ciclo")
        self.combo_categoria.addItem("Fixo — no fim do processo", "fixo_final")
        self.combo_categoria.currentIndexChanged.connect(self._atualizar_visibilidade)
        form_geral.addRow("Categoria:", self.combo_categoria)

        self.spin_ordem = QSpinBox()
        self.spin_ordem.setRange(0, 9999)
        self.spin_ordem.setSingleStep(5)
        form_geral.addRow("Ordem de execução:", self.spin_ordem)
        hint_ordem = QLabel("Números menores executam primeiro. Também dá pra reordenar arrastando na tabela.")
        hint_ordem.setStyleSheet("color: #888; font-size: 11px;")
        form_geral.addRow("", hint_ordem)

        self.check_ativo = QCheckBox("Ativo (desmarque para pular este tipo sem apagar a configuração)")
        form_geral.addRow("", self.check_ativo)

        self.check_ancora = QCheckBox("Usar como âncora de início de ciclo (ex: o Quadro Comparativo)")
        form_geral.addRow("", self.check_ancora)

        aplica_row = QHBoxLayout()
        self.check_dmpp = QCheckBox("DMPP")
        self.check_ufiec = QCheckBox("UFIEC")
        aplica_row.addWidget(self.check_dmpp)
        aplica_row.addWidget(self.check_ufiec)
        aplica_row.addStretch(1)
        form_geral.addRow("Aplica-se a:", aplica_row)

        layout.addLayout(form_geral)

        self.combo_origem = QComboBox()
        self.combo_origem.addItem("Arquivo — vem um PDF/DOCX na pasta", "arquivo")
        self.combo_origem.addItem("Gerado pelo bot — sem arquivo (ex: um despacho)", "gerado")
        self.combo_origem.currentIndexChanged.connect(self._atualizar_visibilidade)
        form_geral.addRow("Origem:", self.combo_origem)

        # ---- Bloco ARQUIVO ----
        self.grupo_arquivo = QGroupBox("Detecção e formulário (origem = arquivo)")
        fa = QFormLayout(self.grupo_arquivo)

        self.combo_modo = QComboBox()
        self.combo_modo.addItem("Interno (cola imagem/texto)", "interno")
        self.combo_modo.addItem("Externo (upload de arquivo)", "externo")
        self.combo_modo.currentIndexChanged.connect(self._atualizar_visibilidade)
        fa.addRow("Modo no SEI:", self.combo_modo)

        self.edit_deteccao = QLineEdit()
        self.edit_deteccao.setPlaceholderText("palavras-chave separadas por vírgula, ex: validacao, validação")
        fa.addRow("Reconhecer pelo nome do arquivo:", self.edit_deteccao)
        hint_det = QLabel(
            "O bot marca esse tipo quando o NOME do arquivo contém qualquer uma "
            "dessas palavras (sem diferenciar maiúsculas/acentos ao comparar)."
        )
        hint_det.setWordWrap(True)
        hint_det.setStyleSheet("color: #888; font-size: 11px;")
        fa.addRow("", hint_det)

        self.edit_busca = QLineEdit()
        fa.addRow("Buscar tipo (campo de busca do SEI):", self.edit_busca)

        self.edit_descricao = QLineEdit()
        fa.addRow("Descrição (formulário interno):", self.edit_descricao)

        self.edit_nome_arvore = QLineEdit()
        fa.addRow("Nome na Árvore (formulário interno):", self.edit_nome_arvore)

        self.edit_tipo_externo = QLineEdit()
        fa.addRow("Tipo (dropdown do formulário externo):", self.edit_tipo_externo)

        self.edit_nome_arvore_fixo = QLineEdit()
        fa.addRow("Nome na Árvore fixo (externo, opcional):", self.edit_nome_arvore_fixo)

        layout.addWidget(self.grupo_arquivo)

        # ---- Bloco GERADO ----
        self.grupo_gerado = QGroupBox("Texto gerado pelo bot (origem = gerado)")
        fg = QVBoxLayout(self.grupo_gerado)

        fg.addWidget(QLabel("Descrição / Nome na Árvore (formulário interno):"))
        linha_desc = QHBoxLayout()
        self.edit_gerado_descricao = QLineEdit()
        self.edit_gerado_descricao.setPlaceholderText("Descrição")
        self.edit_gerado_nome_arvore = QLineEdit()
        self.edit_gerado_nome_arvore.setPlaceholderText("Nome na Árvore")
        linha_desc.addWidget(self.edit_gerado_descricao)
        linha_desc.addWidget(self.edit_gerado_nome_arvore)
        fg.addLayout(linha_desc)
        self.edit_gerado_busca = QLineEdit()
        self.edit_gerado_busca.setPlaceholderText("Buscar tipo (ex: Despacho)")
        fg.addWidget(self.edit_gerado_busca)

        fg.addWidget(QLabel(
            "Template do texto — use { } para inserir valores, ex: {numero_ne}, {data_ne}:"
        ))
        self.txt_template = QPlainTextEdit()
        self.txt_template.setMinimumHeight(100)
        self.txt_template.textChanged.connect(self._atualizar_campos_template)
        fg.addWidget(self.txt_template)

        self.check_captura_link = QCheckBox(
            "Este texto referencia (captura o link de) outro documento já inserido"
        )
        self.check_captura_link.toggled.connect(self._atualizar_visibilidade)
        fg.addWidget(self.check_captura_link)

        self.aviso_link_ciclo = QLabel(
            "⚠️ Captura de link não é permitida em passos de categoria 'Ciclo': a "
            "posição do documento na árvore do SEI muda a cada ciclo, então não "
            "existe uma coordenada fixa segura para calibrar."
        )
        self.aviso_link_ciclo.setWordWrap(True)
        self.aviso_link_ciclo.setStyleSheet("color: #b02a37; font-size: 11px;")
        fg.addWidget(self.aviso_link_ciclo)

        self.grupo_link = QWidget()
        fl = QFormLayout(self.grupo_link)
        self.combo_link_alvo = QComboBox()
        fl.addRow("Capturar link do passo:", self.combo_link_alvo)
        self.coord_dmpp = CoordinateField("Ícone na árvore (DMPP)")
        self.coord_ufiec = CoordinateField("Ícone na árvore (UFIEC)")
        fl.addRow(self.coord_dmpp)
        fl.addRow(self.coord_ufiec)
        info_placeholder_link = QLabel(
            "Use {link} no template no ponto onde o link deve aparecer."
        )
        info_placeholder_link.setStyleSheet("color: #888; font-size: 11px;")
        fl.addRow("", info_placeholder_link)
        fg.addWidget(self.grupo_link)

        fg.addWidget(QLabel("Campos do template (preenchidos automaticamente pelo bot):"))
        self.campos_container = QVBoxLayout()
        self._campo_widgets = {}  # nome -> (combo_fonte, edit_valor_ou_chave)
        campos_wrap = QWidget()
        campos_wrap.setLayout(self.campos_container)
        fg.addWidget(campos_wrap)

        layout.addWidget(self.grupo_gerado)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Salvar")
        buttons.accepted.connect(self._salvar)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ---------------- Carregar valores do passo no formulário ----------------

    def _carregar_valores(self):
        p = self.passo
        self.edit_id.setText(p.get("id", ""))
        idx_cat = {"fixo_inicial": 0, "ciclo": 1, "fixo_final": 2}.get(p.get("categoria"), 1)
        self.combo_categoria.setCurrentIndex(idx_cat)
        self.spin_ordem.setValue(p.get("ordem", 50))
        self.check_ativo.setChecked(p.get("ativo", True))
        self.check_ancora.setChecked(bool(p.get("ancora_ciclo")))

        aplica = p.get("aplica_a", ["DMPP", "UFIEC"])
        self.check_dmpp.setChecked("DMPP" in aplica)
        self.check_ufiec.setChecked("UFIEC" in aplica)

        idx_origem = 0 if p.get("origem", "arquivo") == "arquivo" else 1
        self.combo_origem.setCurrentIndex(idx_origem)

        idx_modo = 0 if p.get("modo", "interno") == "interno" else 1
        self.combo_modo.setCurrentIndex(idx_modo)

        deteccao = p.get("deteccao") or {}
        palavras = deteccao.get("contains_any") or deteccao.get("contains_all") or []
        self.edit_deteccao.setText(", ".join(palavras))

        doc_cfg = p.get("config_doc") or {}
        self.edit_busca.setText(doc_cfg.get("busca", ""))
        self.edit_descricao.setText(doc_cfg.get("descricao", ""))
        self.edit_nome_arvore.setText(doc_cfg.get("nome_arvore", ""))
        self.edit_tipo_externo.setText(doc_cfg.get("tipo_externo", ""))
        self.edit_nome_arvore_fixo.setText(doc_cfg.get("nome_arvore_fixo", ""))

        # Gerado
        self.edit_gerado_busca.setText(doc_cfg.get("busca", ""))
        self.edit_gerado_descricao.setText(doc_cfg.get("descricao", ""))
        self.edit_gerado_nome_arvore.setText(doc_cfg.get("nome_arvore", ""))

        gc = p.get("gerado_config") or {}
        self.txt_template.setPlainText(gc.get("template", ""))
        self.check_captura_link.setChecked(bool(gc.get("captura_link")))

        coords = gc.get("coord_icone_arvore") or {}
        if coords.get("DMPP"):
            self.coord_dmpp.set_value(tuple(coords["DMPP"]))
        if coords.get("UFIEC"):
            self.coord_ufiec.set_value(tuple(coords["UFIEC"]))

        self._popular_combo_link_alvo()
        link_alvo = gc.get("link_step_alvo")
        if link_alvo:
            idx = self.combo_link_alvo.findData(link_alvo)
            if idx >= 0:
                self.combo_link_alvo.setCurrentIndex(idx)

        self._atualizar_campos_template(valores_salvos={c["nome"]: c for c in gc.get("campos", [])})
        self._atualizar_visibilidade()

    def _popular_combo_link_alvo(self):
        self.combo_link_alvo.clear()
        for outro in self.passos_existentes:
            if outro.get("id") == self.passo.get("id"):
                continue
            if outro.get("origem") != "arquivo":
                continue
            self.combo_link_alvo.addItem(outro["id"], outro["id"])

    # ---------------- Placeholders dinâmicos do template ----------------

    def _atualizar_campos_template(self, valores_salvos=None):
        template = self.txt_template.toPlainText()
        placeholders = sorted(set(re.findall(r"\{(\w+)\}", template)))
        placeholders = [p for p in placeholders if p != "link"]

        # limpa widgets antigos
        while self.campos_container.count():
            item = self.campos_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._campo_widgets = {}

        for nome in placeholders:
            linha = QHBoxLayout()
            linha.addWidget(QLabel(f"{{{nome}}}:"))

            combo_fonte = QComboBox()
            combo_fonte.addItem("Valor fixo", "fixo")
            combo_fonte.addItem("Vem de outro passo (contexto)", "contexto")
            edit_valor = QLineEdit()

            salvo = (valores_salvos or {}).get(nome)
            if salvo:
                if salvo.get("fonte") == "contexto":
                    combo_fonte.setCurrentIndex(1)
                    edit_valor.setText(salvo.get("chave", ""))
                    edit_valor.setPlaceholderText("chave no contexto, ex: ne_numero")
                else:
                    combo_fonte.setCurrentIndex(0)
                    edit_valor.setText(salvo.get("valor", ""))
            else:
                edit_valor.setPlaceholderText("valor fixo, ou nome da chave se vier de outro passo")

            linha.addWidget(combo_fonte)
            linha.addWidget(edit_valor, 1)
            wrap = QWidget()
            wrap.setLayout(linha)
            self.campos_container.addWidget(wrap)
            self._campo_widgets[nome] = (combo_fonte, edit_valor)

    # ---------------- Mostrar/esconder blocos conforme escolhas ----------------

    def _atualizar_visibilidade(self):
        origem = self.combo_origem.currentData()
        categoria = self.combo_categoria.currentData()
        modo = self.combo_modo.currentData()

        self.grupo_arquivo.setVisible(origem == "arquivo")
        self.grupo_gerado.setVisible(origem == "gerado")

        self.edit_busca.setVisible(True)
        eh_interno = (modo == "interno")
        self.edit_descricao.setVisible(eh_interno)
        self.edit_nome_arvore.setVisible(eh_interno)
        self.edit_tipo_externo.setVisible(not eh_interno)
        self.edit_nome_arvore_fixo.setVisible(not eh_interno)

        self.check_ancora.setVisible(categoria == "ciclo")
        if categoria != "ciclo":
            self.check_ancora.setChecked(False)

        pode_capturar_link = (categoria != "ciclo")
        self.check_captura_link.setEnabled(pode_capturar_link)
        if not pode_capturar_link:
            self.check_captura_link.setChecked(False)
        self.aviso_link_ciclo.setVisible(categoria == "ciclo")

        self.grupo_link.setVisible(self.check_captura_link.isChecked() and pode_capturar_link)

    # ---------------- Salvar ----------------

    def _salvar(self):
        novo_id = self.edit_id.text().strip()
        if not novo_id:
            QMessageBox.warning(self, "Campo obrigatório", "Preencha o identificador interno.")
            return
        if not re.match(r"^[a-z][a-z0-9_]*$", novo_id):
            QMessageBox.warning(
                self, "Identificador inválido",
                "Use só letras minúsculas, números e underscore, começando por letra "
                "(ex: despacho_validacao)."
            )
            return
        ids_existentes = {p["id"] for p in self.passos_existentes if p.get("id") != (self.passo_original or {}).get("id")}
        if novo_id in ids_existentes:
            QMessageBox.warning(self, "Identificador em uso", f"Já existe um passo com id '{novo_id}'.")
            return

        aplica_a = [t for t, chk in (("DMPP", self.check_dmpp), ("UFIEC", self.check_ufiec)) if chk.isChecked()]
        if not aplica_a:
            QMessageBox.warning(self, "Selecione ao menos um", "O passo precisa se aplicar a DMPP e/ou UFIEC.")
            return

        categoria = self.combo_categoria.currentData()
        origem = self.combo_origem.currentData()
        modo = self.combo_modo.currentData()

        passo = dict(self.passo)
        passo["id"] = novo_id
        passo["categoria"] = categoria
        passo["ordem"] = self.spin_ordem.value()
        passo["ativo"] = self.check_ativo.isChecked()
        passo["ancora_ciclo"] = self.check_ancora.isChecked() and categoria == "ciclo"
        passo["aplica_a"] = aplica_a
        passo["origem"] = origem
        passo["modo"] = modo

        if origem == "arquivo":
            palavras = [p.strip() for p in self.edit_deteccao.text().split(",") if p.strip()]
            passo["deteccao"] = {"contains_any": palavras}
            config_doc = {"busca": self.edit_busca.text().strip()}
            if modo == "interno":
                config_doc["descricao"] = self.edit_descricao.text().strip()
                config_doc["nome_arvore"] = self.edit_nome_arvore.text().strip()
            else:
                config_doc["tipo_externo"] = self.edit_tipo_externo.text().strip()
                if self.edit_nome_arvore_fixo.text().strip():
                    config_doc["nome_arvore_fixo"] = self.edit_nome_arvore_fixo.text().strip()
            passo["config_doc"] = config_doc

            # só toca no processor se for passo novo ou se não tinha um
            # processor "de fábrica" — nunca sobrescreve lógica bespoke.
            if not passo.get("processor") or passo["processor"] in (
                "generico_imagem_pdf", "generico_upload_externo"
            ):
                passo["processor"] = "generico_imagem_pdf" if modo == "interno" else "generico_upload_externo"
            passo["gerado_config"] = None
        else:
            passo["deteccao"] = None
            passo["processor"] = "despacho_gerado"
            passo["config_doc"] = {
                "busca": self.edit_gerado_busca.text().strip() or "Despacho",
                "descricao": self.edit_gerado_descricao.text().strip(),
                "nome_arvore": self.edit_gerado_nome_arvore.text().strip() or novo_id,
            }

            campos = []
            for nome, (combo_fonte, edit_valor) in self._campo_widgets.items():
                if combo_fonte.currentData() == "contexto":
                    campos.append({"nome": nome, "fonte": "contexto", "chave": edit_valor.text().strip() or nome})
                else:
                    campos.append({"nome": nome, "fonte": "fixo", "valor": edit_valor.text()})

            captura_link = self.check_captura_link.isChecked() and categoria != "ciclo"
            gerado_config = {
                "template": self.txt_template.toPlainText(),
                "campos": campos,
                "captura_link": captura_link,
            }
            if captura_link:
                gerado_config["link_step_alvo"] = self.combo_link_alvo.currentData()
                coords = {}
                if self.coord_dmpp.get_value():
                    coords["DMPP"] = list(self.coord_dmpp.get_value())
                if self.coord_ufiec.get_value():
                    coords["UFIEC"] = list(self.coord_ufiec.get_value())
                gerado_config["coord_icone_arvore"] = coords
            passo["gerado_config"] = gerado_config

        # valida contra o resto do pipeline antes de aceitar
        outros = [p for p in self.passos_existentes if p.get("id") != (self.passo_original or {}).get("id")]
        erros = pipeline.validar_pipeline(outros + [passo])
        if erros:
            QMessageBox.warning(self, "Configuração inválida", "\n".join(erros))
            return

        self.passo = passo
        self.accept()
