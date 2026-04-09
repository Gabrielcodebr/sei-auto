# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec para SEI Automation GUI.

Build:
    pyinstaller SeiAuto.spec --clean --noconfirm

Ou simplesmente:
    build_exe.bat
"""

import os

block_cipher = None

# Inclui pasta de referências de imagens como dado (se existir)
datas = []
if os.path.isdir("img_references"):
    datas.append(("img_references", "img_references"))

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "keyboard",
    "win32com",
    "win32com.client",
    "pytesseract",
    "fitz",  # PyMuPDF
    "docx",
    "pyautogui",
    "pyperclip",
    "PIL",
]

a = Analysis(
    ["main_gui.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy.distutils", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SeiAuto",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # sem console preto atrás da GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,               # Coloque aqui um .ico se quiser ícone customizado
)
