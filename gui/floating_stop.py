"""
Mini-janela flutuante "always on top" com botão STOP gigante.

Aparece enquanto a automação está rodando, permitindo ao usuário
parar sem precisar trazer a janela principal da GUI para frente.
"""

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

from gui.stop_controller import stop_controller


class FloatingStopWindow(QWidget):
    """Janela frameless, always-on-top, arrastável, com botão STOP."""

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(240, 90)

        self.setStyleSheet(
            """
            QWidget {
                background-color: #222;
                border: 2px solid #c0392b;
                border-radius: 8px;
            }
            QLabel {
                color: #f5f5f5;
                font-weight: bold;
                background: transparent;
                border: none;
            }
            QPushButton {
                background-color: #c0392b;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #e74c3c; }
            QPushButton:pressed { background-color: #962d22; }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)

        self.label = QLabel("AUTOMAÇÃO RODANDO")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.btn_stop = QPushButton("PARAR  (F12)")
        self.btn_stop.clicked.connect(self._on_stop)
        layout.addWidget(self.btn_stop)

        self._drag_offset = None
        self._position_top_right()

    def _position_top_right(self):
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        x = geo.right() - self.width() - 20
        y = geo.top() + 20
        self.move(x, y)

    def _on_stop(self):
        self.btn_stop.setEnabled(False)
        self.label.setText("PARANDO...")
        stop_controller.request_stop()

    # ---- arrastar a janela ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        event.accept()

    def show_running(self):
        self.btn_stop.setEnabled(True)
        self.label.setText("AUTOMAÇÃO RODANDO")
        self.show()
        self.raise_()
