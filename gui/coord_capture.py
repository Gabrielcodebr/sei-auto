"""
Widget para editar e capturar uma coordenada (x, y) da tela.

- Mostra nome do campo + dois QSpinBox (x, y).
- Botão "Capturar" → countdown de 3s → pega posição atual do mouse.
- Botão "Ver" → move cursor do mouse para as coordenadas atuais.
"""

import pyautogui
from PySide6.QtCore import QTimer, Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QSpinBox, QPushButton
)


class CoordinateField(QWidget):
    """Campo editável de coordenada (x, y) com captura assistida."""

    value_changed = Signal()

    def __init__(self, label: str, value=(0, 0), parent=None):
        super().__init__(parent)
        self._building = True

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)

        self.label = QLabel(label)
        self.label.setMinimumWidth(280)
        layout.addWidget(self.label)

        layout.addWidget(QLabel("X:"))
        self.spin_x = QSpinBox()
        self.spin_x.setRange(0, 9999)
        self.spin_x.setFixedWidth(75)
        layout.addWidget(self.spin_x)

        layout.addWidget(QLabel("Y:"))
        self.spin_y = QSpinBox()
        self.spin_y.setRange(0, 9999)
        self.spin_y.setFixedWidth(75)
        layout.addWidget(self.spin_y)

        self.btn_capture = QPushButton("🎯 Capturar")
        self.btn_capture.setToolTip("Clique e mova o mouse ao ponto desejado em 3 segundos.")
        self.btn_capture.clicked.connect(self._start_capture)
        layout.addWidget(self.btn_capture)

        self.btn_view = QPushButton("👁 Ver")
        self.btn_view.setToolTip("Move o cursor para este ponto (para conferência).")
        self.btn_view.clicked.connect(self._view)
        layout.addWidget(self.btn_view)

        layout.addStretch(1)

        self.set_value(value)
        self.spin_x.valueChanged.connect(self._emit_changed)
        self.spin_y.valueChanged.connect(self._emit_changed)
        self._building = False

        # Countdown timer
        self._countdown = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

    def _emit_changed(self):
        if not self._building:
            self.value_changed.emit()

    def set_value(self, value):
        if not value or len(value) < 2:
            value = (0, 0)
        self.spin_x.setValue(int(value[0]))
        self.spin_y.setValue(int(value[1]))

    def get_value(self) -> tuple:
        return (self.spin_x.value(), self.spin_y.value())

    def _start_capture(self):
        self._countdown = 3
        self.btn_capture.setEnabled(False)
        self.btn_capture.setText(f"Capturando em {self._countdown}...")
        self._timer.start()

    def _tick(self):
        self._countdown -= 1
        if self._countdown <= 0:
            self._timer.stop()
            x, y = pyautogui.position()
            self.set_value((x, y))
            self.btn_capture.setEnabled(True)
            self.btn_capture.setText("🎯 Capturar")
            self.value_changed.emit()
        else:
            self.btn_capture.setText(f"Capturando em {self._countdown}...")

    def _view(self):
        x, y = self.get_value()
        try:
            pyautogui.moveTo(x, y, duration=0.3)
        except Exception as e:
            print(f"[coord_capture] Erro ao mover cursor: {e}")


class RegionField(QWidget):
    """Campo para região (x, y, largura, altura) — 4 SpinBox."""

    value_changed = Signal()

    def __init__(self, label: str, value=(0, 0, 0, 0), parent=None):
        super().__init__(parent)
        self._building = True

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)

        self.label = QLabel(label)
        self.label.setMinimumWidth(280)
        layout.addWidget(self.label)

        self.spins = []
        for tag in ("X:", "Y:", "L:", "A:"):
            layout.addWidget(QLabel(tag))
            spin = QSpinBox()
            spin.setRange(0, 9999)
            spin.setFixedWidth(70)
            spin.valueChanged.connect(self._emit_changed)
            layout.addWidget(spin)
            self.spins.append(spin)

        layout.addStretch(1)
        self.set_value(value)
        self._building = False

    def _emit_changed(self):
        if not self._building:
            self.value_changed.emit()

    def set_value(self, value):
        if not value or len(value) < 4:
            value = (0, 0, 0, 0)
        for spin, v in zip(self.spins, value):
            spin.setValue(int(v))

    def get_value(self) -> tuple:
        return tuple(s.value() for s in self.spins)
