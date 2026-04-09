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
            return

        def chave(nome):
            m = re.match(r"^(\d+)", nome)
            return int(m.group(1)) if m else 9999

        arquivos = sorted(
            [f for f in os.listdir(path) if f.lower().endswith((".pdf", ".docx"))],
            key=chave,
        )

        self.tbl.setRowCount(len(arquivos))
        for row, nome in enumerate(arquivos):
            numero = re.match(r"^(\d+)", nome)
            num_str = numero.group(1) if numero else "?"
            full = os.path.join(path, nome)
            size = _formatar_tamanho(os.path.getsize(full))
            tipo = _identificar_tipo(nome)

            self.tbl.setItem(row, 0, QTableWidgetItem(num_str))
            self.tbl.setItem(row, 1, QTableWidgetItem(nome))
            self.tbl.setItem(row, 2, QTableWidgetItem(tipo))
            self.tbl.setItem(row, 3, QTableWidgetItem(size))

        self.lbl_count.setText(f"📄 {len(arquivos)} arquivo(s) encontrado(s)")

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
