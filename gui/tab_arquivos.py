"""
Aba "Documentos" — lista os arquivos da pasta DOCUMENTOS_DIR
com tipo detectado e tamanho, para conferência antes de executar.
"""

import os
import re
import subprocess
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)

import config
import doc_ordem
from gui.dialog_resolver_ordem import DialogResolverOrdem


def _formatar_tamanho(bytes_: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unit}"
        bytes_ /= 1024
    return f"{bytes_:.1f} TB"


def _identificar_tipo(nome: str) -> str:
    """Heurística leve (sem depender de instanciar SEIAutomation)."""
    nome_lower = nome.lower()
    if re.search(r"\bcapa\b", nome_lower):
        return "Capa"
    if "solicita" in nome_lower:
        return "Solicitação"
    if "memorando" in nome_lower or "justificativ" in nome_lower:
        return "Memorando/Justificativa"
    if "nota" in nome_lower and "empenho" in nome_lower:
        return "Nota de Empenho"
    if "despacho" in nome_lower:
        return "Despacho"
    if "ordem" in nome_lower and "banc" in nome_lower:
        return "Ordem Bancária"
    if "quadro" in nome_lower or "comparativ" in nome_lower or "planilha" in nome_lower:
        return "Quadro Comparativo"
    if "nota fiscal" in nome_lower or re.search(r"\bnf\b", nome_lower):
        return "Nota Fiscal"
    if "comprovante" in nome_lower and "iss" in nome_lower:
        return "Comprovante ISS"
    if "iss" in nome_lower and ("guia" in nome_lower or "empresa" in nome_lower):
        return "Guia ISS"
    if "comprovante" in nome_lower:
        return "Comprovante Fiscal"
    if "declara" in nome_lower and "recebimento" in nome_lower:
        return "Declaração de Recebimento"
    if "declara" in nome_lower and "encerramento" in nome_lower:
        return "Declaração de Encerramento"
    if "optante" in nome_lower or "consulta" in nome_lower:
        return "Consulta Optante"
    if "cnpj" in nome_lower:
        return "CNPJ"
    if "balancete" in nome_lower:
        return "Balancete"
    if "extrato" in nome_lower:
        return "Extrato Bancário"
    if "concilia" in nome_lower:
        return "Conciliação Contábil"
    return "—"


class TabArquivos(QWidget):
    """Preview dos documentos na pasta antes de executar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grupos_dispensados = set()  # chaves de grupo com "agora não" nesta sessão
        self._build_ui()
        self.reload()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QHBoxLayout()
        self.lbl_path = QLabel()
        self.lbl_path.setStyleSheet("font-weight: bold;")
        header.addWidget(self.lbl_path, 1)

        self.btn_abrir = QPushButton("📁 Abrir pasta")
        self.btn_abrir.clicked.connect(self._open_folder)
        header.addWidget(self.btn_abrir)

        self.btn_reload = QPushButton("🔄 Recarregar")
        self.btn_reload.clicked.connect(self.reload)
        header.addWidget(self.btn_reload)

        layout.addLayout(header)

        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet("color: #555;")
        layout.addWidget(self.lbl_count)

        # Banner de conflito de numeração (some quando não há conflitos)
        banner_row = QHBoxLayout()
        self.banner_conflito = QLabel()
        self.banner_conflito.setWordWrap(True)
        self.banner_conflito.setStyleSheet(
            "background-color: #fdecea; color: #611a15; padding: 8px; "
            "border: 1px solid #f5c6cb; border-radius: 4px;"
        )
        self.banner_conflito.hide()
        banner_row.addWidget(self.banner_conflito, 1)

        self.btn_resolver = QPushButton("⚠️ Resolver ordem")
        self.btn_resolver.clicked.connect(self._resolver_conflitos)
        self.btn_resolver.hide()
        banner_row.addWidget(self.btn_resolver)
        layout.addLayout(banner_row)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(4)
        self.tbl.setHorizontalHeaderLabels(["Nº", "Arquivo", "Tipo detectado", "Tamanho"])
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tbl, 1)

    def reload(self):
        path = config.DOCUMENTOS_DIR
        self.lbl_path.setText(f"Pasta: {path}")

        if not os.path.isdir(path):
            self.lbl_count.setText("⚠️ Pasta não encontrada.")
            self.tbl.setRowCount(0)
            self.banner_conflito.hide()
            self.btn_resolver.hide()
            return

        def chave(nome):
            m = re.match(r"^(\d+)", nome)
            return int(m.group(1)) if m else 9999

        arquivos = sorted(
            [f for f in os.listdir(path) if f.lower().endswith((".pdf", ".docx"))],
            key=chave,
        )

        pendentes = doc_ordem.conflitos_pendentes(path, config.BASE_DIR)
        nomes_em_conflito = {nome for grupo in pendentes for nome in grupo}

        self.tbl.setRowCount(len(arquivos))
        for row, nome in enumerate(arquivos):
            numero = re.match(r"^(\d+)", nome)
            num_str = numero.group(1) if numero else "?"
            full = os.path.join(path, nome)
            size = _formatar_tamanho(os.path.getsize(full))
            tipo = _identificar_tipo(nome)

            valores = (num_str, nome, tipo, size)
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                if nome in nomes_em_conflito:
                    item.setBackground(Qt.yellow)
                    item.setToolTip("Número em conflito com outro arquivo — ordem ambígua")
                self.tbl.setItem(row, col, item)

        self.lbl_count.setText(f"📄 {len(arquivos)} arquivo(s) encontrado(s)")

        if not pendentes:
            self.banner_conflito.hide()
            self.btn_resolver.hide()
            return

        self.banner_conflito.setText(
            f"⚠️ {len(pendentes)} conflito(s) de numeração encontrado(s): dois ou "
            "mais arquivos com o mesmo número (destacados em amarelo). A ordem "
            "entre eles é ambígua — resolva antes de executar."
        )
        self.banner_conflito.show()
        self.btn_resolver.show()

        novos = [g for g in pendentes if doc_ordem.chave_grupo(g) not in self._grupos_dispensados]
        if novos:
            resp = QMessageBox.warning(
                self, "Conflito de numeração",
                f"Encontrei {len(novos)} conflito(s) de numeração na pasta de "
                "documentos: arquivos diferentes com o mesmo número, então a "
                "ordem de processamento fica ambígua.\n\n"
                "Quer decidir a ordem agora?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
            )
            if resp == QMessageBox.Yes:
                self._resolver_conflitos()
                return  # _resolver_conflitos() já chama reload() de novo
            for g in novos:
                self._grupos_dispensados.add(doc_ordem.chave_grupo(g))

    def _resolver_conflitos(self):
        """Abre o diálogo 'Qual arquivo é primeiro?' para cada conflito pendente."""
        path = config.DOCUMENTOS_DIR
        pendentes = doc_ordem.conflitos_pendentes(path, config.BASE_DIR)
        for grupo in pendentes:
            dlg = DialogResolverOrdem(grupo, self)
            dlg.exec()
        self.reload()

    def _open_folder(self):
        path = config.DOCUMENTOS_DIR
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Pasta não encontrada", path)
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            QMessageBox.warning(self, "Erro", str(e))
