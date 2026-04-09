"""
Aba "Executar" — substitui os menus de terminal do sei_automation.py.

Componentes:
- Seleção de tipo de processo (DMPP / UFIEC)
- Seleção de modo (do início / pular fixos / ciclo específico / arquivo específico)
- Botão Iniciar com countdown
- Log em tempo real
- Integração com mini-janela flutuante + hotkey F12 para parar
"""

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton, QSpinBox,
    QPushButton, QPlainTextEdit, QLabel, QMessageBox
)

from gui.automation_worker import AutomationWorker
from gui.floating_stop import FloatingStopWindow
from gui.stop_controller import stop_controller


class TabExecutar(QWidget):
    """Aba principal de execução da automação."""

    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: AutomationWorker | None = None
        self.floating_stop: FloatingStopWindow | None = None
        self._countdown = 0
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._tick_countdown)

        self._build_ui()
        stop_controller.stop_requested.connect(self._on_stop_requested)

    # ---------------- UI ----------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Linha: tipo de processo + modo
        top_row = QHBoxLayout()

        # --- Tipo de processo ---
        gb_tipo = QGroupBox("Tipo de Processo")
        vt = QVBoxLayout(gb_tipo)
        self.rb_dmpp = QRadioButton("DMPP (padrão)")
        self.rb_ufiec = QRadioButton("UFIEC (com memorando)")
        self.rb_dmpp.setChecked(True)
        vt.addWidget(self.rb_dmpp)
        vt.addWidget(self.rb_ufiec)
        top_row.addWidget(gb_tipo, 1)

        # --- Modo de execução ---
        gb_modo = QGroupBox("Modo de Execução")
        vm = QVBoxLayout(gb_modo)
        self.rb_inicio = QRadioButton("Executar do início (todos os documentos)")
        self.rb_pular = QRadioButton("Pular documentos fixos (começar do ciclo 1)")
        self.rb_ciclo = QRadioButton("Começar de um ciclo específico:")
        self.rb_arquivo = QRadioButton("Começar de um arquivo específico (número):")
        self.rb_inicio.setChecked(True)

        self.spin_ciclo = QSpinBox()
        self.spin_ciclo.setRange(1, 999)
        self.spin_ciclo.setValue(1)
        self.spin_ciclo.setEnabled(False)

        self.spin_arquivo = QSpinBox()
        self.spin_arquivo.setRange(1, 9999)
        self.spin_arquivo.setValue(1)
        self.spin_arquivo.setEnabled(False)

        vm.addWidget(self.rb_inicio)
        vm.addWidget(self.rb_pular)

        line_ciclo = QHBoxLayout()
        line_ciclo.addWidget(self.rb_ciclo)
        line_ciclo.addWidget(self.spin_ciclo)
        line_ciclo.addStretch(1)
        vm.addLayout(line_ciclo)

        line_arquivo = QHBoxLayout()
        line_arquivo.addWidget(self.rb_arquivo)
        line_arquivo.addWidget(self.spin_arquivo)
        line_arquivo.addStretch(1)
        vm.addLayout(line_arquivo)

        self.rb_ciclo.toggled.connect(self.spin_ciclo.setEnabled)
        self.rb_arquivo.toggled.connect(self.spin_arquivo.setEnabled)

        top_row.addWidget(gb_modo, 2)
        root.addLayout(top_row)

        # --- Botões ---
        btn_row = QHBoxLayout()
        self.btn_iniciar = QPushButton("▶  INICIAR AUTOMAÇÃO")
        self.btn_iniciar.setMinimumHeight(48)
        self.btn_iniciar.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; "
            "font-weight: bold; font-size: 14px; border-radius: 6px; } "
            "QPushButton:hover { background-color: #2ecc71; } "
            "QPushButton:disabled { background-color: #7f8c8d; }"
        )
        self.btn_iniciar.clicked.connect(self._start_countdown)
        btn_row.addWidget(self.btn_iniciar, 2)

        self.btn_cancelar_countdown = QPushButton("Cancelar countdown")
        self.btn_cancelar_countdown.setEnabled(False)
        self.btn_cancelar_countdown.clicked.connect(self._cancel_countdown)
        btn_row.addWidget(self.btn_cancelar_countdown, 1)

        self.btn_parar = QPushButton("⏹  PARAR  (F12)")
        self.btn_parar.setEnabled(False)
        self.btn_parar.setStyleSheet(
            "QPushButton { background-color: #c0392b; color: white; "
            "font-weight: bold; border-radius: 6px; padding: 8px; } "
            "QPushButton:hover { background-color: #e74c3c; } "
            "QPushButton:disabled { background-color: #7f8c8d; }"
        )
        self.btn_parar.clicked.connect(self._request_stop)
        btn_row.addWidget(self.btn_parar, 1)

        root.addLayout(btn_row)

        # --- Status ---
        self.lbl_status = QLabel("Pronto")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("font-weight: bold; padding: 4px;")
        root.addWidget(self.lbl_status)

        # --- Log ---
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)
        self.log.setFont(mono)
        self.log.setStyleSheet(
            "QPlainTextEdit { background-color: #1e1e1e; color: #e0e0e0; "
            "border: 1px solid #444; }"
        )
        root.addWidget(self.log, 1)

    # ---------------- Lógica ----------------

    def _get_opcoes(self) -> dict:
        tipo = "UFIEC" if self.rb_ufiec.isChecked() else "DMPP"
        if self.rb_inicio.isChecked():
            return {
                "tipo_processo": tipo,
                "pular_docs_fixos": False,
                "ciclo_inicial": 1,
                "arquivo_inicial": None,
            }
        if self.rb_pular.isChecked():
            return {
                "tipo_processo": tipo,
                "pular_docs_fixos": True,
                "ciclo_inicial": 1,
                "arquivo_inicial": None,
            }
        if self.rb_ciclo.isChecked():
            return {
                "tipo_processo": tipo,
                "pular_docs_fixos": True,
                "ciclo_inicial": self.spin_ciclo.value(),
                "arquivo_inicial": None,
            }
        # rb_arquivo
        return {
            "tipo_processo": tipo,
            "pular_docs_fixos": True,
            "ciclo_inicial": 1,
            "arquivo_inicial": self.spin_arquivo.value(),
        }

    def _start_countdown(self):
        self._countdown = 10
        self.btn_iniciar.setEnabled(False)
        self.btn_cancelar_countdown.setEnabled(True)
        self._set_status(f"Iniciando em {self._countdown}s... (posicione o SEI)")
        self._append_log(f"⏳ Iniciando em {self._countdown} segundos...")
        self._countdown_timer.start()

    def _tick_countdown(self):
        self._countdown -= 1
        if self._countdown <= 0:
            self._countdown_timer.stop()
            self.btn_cancelar_countdown.setEnabled(False)
            self._launch_worker()
        else:
            self._set_status(f"Iniciando em {self._countdown}s...")
            self._append_log(f"   {self._countdown}...")

    def _cancel_countdown(self):
        self._countdown_timer.stop()
        self.btn_iniciar.setEnabled(True)
        self.btn_cancelar_countdown.setEnabled(False)
        self._set_status("Cancelado")
        self._append_log("⚠️ Countdown cancelado.")

    def _launch_worker(self):
        opcoes = self._get_opcoes()
        self._append_log("\n🚀 INICIANDO AUTOMAÇÃO...\n")
        self._set_status("Executando...")

        self.worker = AutomationWorker(opcoes)
        self.worker.log_line.connect(self._append_log)
        self.worker.finished_ok.connect(self._on_finished_ok)
        self.worker.finished_error.connect(self._on_finished_error)
        self.worker.stopped_by_user.connect(self._on_stopped)
        self.worker.finished.connect(self._cleanup_after_run)

        self.btn_parar.setEnabled(True)

        if self.floating_stop is None:
            self.floating_stop = FloatingStopWindow()
        self.floating_stop.show_running()

        self.worker.start()

    def _request_stop(self):
        self._append_log("\n⚠️ Parada solicitada pelo usuário — aguardando próximo checkpoint...")
        self.btn_parar.setEnabled(False)
        stop_controller.request_stop()

    def _on_stop_requested(self):
        """Chamado pelo signal do stop_controller (F12 ou botão flutuante)."""
        self.btn_parar.setEnabled(False)
        self._append_log("\n⚠️ Parada solicitada — aguardando próximo checkpoint...")

    def _on_finished_ok(self):
        self._set_status("✅ Concluído com sucesso")
        self._append_log("\n✅ Processo finalizado com sucesso!")

    def _on_finished_error(self, msg: str):
        self._set_status("❌ Erro")
        self._append_log(f"\n❌ Erro: {msg}")
        QMessageBox.critical(self, "Erro na automação", msg)

    def _on_stopped(self):
        self._set_status("⏹ Parado pelo usuário")
        self._append_log("\n⏹ Automação interrompida pelo usuário.")

    def _cleanup_after_run(self):
        self.btn_iniciar.setEnabled(True)
        self.btn_parar.setEnabled(False)
        if self.floating_stop is not None:
            self.floating_stop.hide()
        self.worker = None

    def _append_log(self, line: str):
        self.log.appendPlainText(line)

    def _set_status(self, text: str):
        self.lbl_status.setText(text)
        self.status_changed.emit(text)

    def is_running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()
