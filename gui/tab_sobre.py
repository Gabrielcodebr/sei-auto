"""
Aba "Sobre" — informações do projeto e atalhos úteis.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout


ABOUT_HTML = """
<h2>🤖 SEI Automation</h2>
<p><b>Sistema de Inserção Automática de Documentos no SEI (SP)</b></p>
<p>Interface gráfica construída com PySide6 sobre a lógica de automação existente
em <code>sei_automation.py</code>.</p>

<h3>Atalhos úteis</h3>
<ul>
  <li><b>F12</b> — para a automação a qualquer momento (mesmo sem a janela em foco)</li>
  <li><b>Mouse no canto superior esquerdo</b> — failsafe nativo do pyautogui</li>
  <li>Mini-janela flutuante aparece automaticamente enquanto a automação roda</li>
</ul>

<h3>Dicas</h3>
<ul>
  <li>Configure coordenadas na aba <b>Configurações → Coordenadas</b> (botão 🎯 Capturar)</li>
  <li>Resolução base testada: <b>1600x900</b> com Firefox maximizado</li>
  <li>As mudanças ficam em <code>user_config.json</code> — delete para voltar aos padrões</li>
  <li>O Tesseract OCR precisa estar instalado separadamente</li>
</ul>

<h3>Versão</h3>
<p>GUI 1.0 — sobre automação 2.0</p>
"""


class TabSobre(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel(ABOUT_HTML)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        label.setAlignment(Qt.AlignTop)
        layout.addWidget(label, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addStretch(1)
        layout.addLayout(row)
