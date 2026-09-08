"""
Diálogo "Qual arquivo é primeiro?" — deixa o usuário decidir a ordem
entre arquivos que têm o mesmo número de prefixo (conflito de
numeração detectado por doc_ordem.py).

Não renomeia nada em disco: só grava a ordem escolhida em
ordem_manual.json (via doc_ordem.resolver_conflito).
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QDialogButtonBox
)

import config
import doc_ordem


class DialogResolverOrdem(QDialog):
    """Resolve UM grupo de conflito por vez (chame de novo para cada grupo)."""

    def __init__(self, grupo, parent=None):
        super().__init__(parent)
        self.grupo = list(grupo)
        self.setWindowTitle("Qual arquivo é primeiro?")
        self.resize(560, 320)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        lbl = QLabel(
            "Estes arquivos têm o MESMO número — a ordem entre eles é "
            "ambígua. Selecione um arquivo e use ↑ / ↓ até deixá-los na "
            "ordem correta de processamento (o primeiro da lista é "
            "processado primeiro). Os arquivos NÃO serão renomeados."
        )
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        self.list_widget = QListWidget()
        self.list_widget.addItems(self.grupo)
        self.list_widget.setCurrentRow(0)
        layout.addWidget(self.list_widget, 1)

        btn_row = QHBoxLayout()
        self.btn_up = QPushButton("↑ Mover para cima")
        self.btn_down = QPushButton("↓ Mover para baixo")
        self.btn_up.clicked.connect(self._move_up)
        self.btn_down.clicked.connect(self._move_down)
        btn_row.addWidget(self.btn_up)
        btn_row.addWidget(self.btn_down)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Confirmar ordem")
        buttons.accepted.connect(self._confirmar)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            self.list_widget.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list_widget.currentRow()
        if 0 <= row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
            self.list_widget.setCurrentRow(row + 1)

    def _confirmar(self):
        ordem_escolhida = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        doc_ordem.resolver_conflito(config.BASE_DIR, self.grupo, ordem_escolhida)
        self.accept()
