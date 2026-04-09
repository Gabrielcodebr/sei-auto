"""
Janela principal da GUI — QMainWindow com QTabWidget.

Abas:
1. Executar (menu + log ao vivo)
2. Documentos (preview dos arquivos)
3. Configurações (editor de coordenadas, tempos, textos...)
4. Sobre
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QMessageBox, QStatusBar, QLabel
)

from gui.tab_executar import TabExecutar
from gui.tab_arquivos import TabArquivos
from gui.tab_configuracoes import TabConfiguracoes
from gui.tab_sobre import TabSobre
from gui.stop_controller import stop_controller


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SEI Automation — Interface Gráfica")
        self.resize(1100, 780)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tab_executar = TabExecutar()
        self.tab_arquivos = TabArquivos()
        self.tab_config = TabConfiguracoes()
        self.tab_sobre = TabSobre()

        self.tabs.addTab(self.tab_executar, "▶  Executar")
        self.tabs.addTab(self.tab_arquivos, "📄  Documentos")
        self.tabs.addTab(self.tab_config, "⚙  Configurações")
        self.tabs.addTab(self.tab_sobre, "ℹ  Sobre")

        # Status bar
        self.setStatusBar(QStatusBar())
        self.lbl_hint = QLabel("  Pressione F12 durante a execução para parar")
        self.statusBar().addPermanentWidget(self.lbl_hint)

        # Recarrega lista de documentos quando trocar para aba correspondente
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Conecta signal do worker para recarregar lista de docs no fim
        self.tab_executar.status_changed.connect(self.statusBar().showMessage)

        # Registra hotkey global F12
        stop_controller.register_hotkey("f12")

        # Valida configurações ao abrir e avisa no log
        self._validate_on_startup()

    def _on_tab_changed(self, index: int):
        if self.tabs.widget(index) is self.tab_arquivos:
            self.tab_arquivos.reload()

    def _validate_on_startup(self):
        import os
        import config
        problemas = []
        if not os.path.exists(config.TESSERACT_PATH):
            problemas.append(f"Tesseract não encontrado: {config.TESSERACT_PATH}")
        if not os.path.exists(config.DOCUMENTOS_DIR):
            problemas.append(f"Pasta de documentos não encontrada: {config.DOCUMENTOS_DIR}")

        if problemas:
            msg = "\n".join(f"⚠️ {p}" for p in problemas)
            msg += "\n\nConfigure na aba 'Configurações → Caminhos & OCR'."
            QMessageBox.warning(self, "Verificação inicial", msg)

    def closeEvent(self, event: QCloseEvent):
        # Se automação estiver rodando, confirma
        if self.tab_executar.is_running():
            resp = QMessageBox.question(
                self, "Automação em execução",
                "A automação está rodando. Deseja pará-la e sair?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                event.ignore()
                return
            stop_controller.request_stop()

        # Se houver alterações não salvas nas configurações
        if self.tab_config.has_unsaved_changes():
            resp = QMessageBox.question(
                self, "Alterações não salvas",
                "Há alterações não salvas em Configurações. Sair mesmo assim?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                event.ignore()
                return

        stop_controller.unregister_hotkey()
        event.accept()
