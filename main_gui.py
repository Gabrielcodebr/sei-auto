"""
SEI Automation — Interface Gráfica (PySide6)

Ponto de entrada. Execução:
    python main_gui.py

Ou, depois de construído com PyInstaller:
    SeiAuto.exe
"""

import os
import sys
from pathlib import Path


def _ensure_cwd():
    """Garante que o CWD é a raiz do projeto, independente de como foi
    executado (python main_gui.py, clique no .exe, etc.)."""
    base = Path(__file__).resolve().parent
    os.chdir(base)
    # Inclui base no sys.path para poder importar config/sei_automation
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))


def main():
    _ensure_cwd()

    # Carrega overrides do user_config.json ANTES de importar sei_automation.
    # Como config.py já tem o hook no final, basta garantir que ele seja
    # importado com os overrides aplicados.
    from gui.config_manager import load_user_config
    load_user_config()

    from PySide6.QtWidgets import QApplication
    from gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("SEI Automation")
    app.setOrganizationName("sei-auto")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
