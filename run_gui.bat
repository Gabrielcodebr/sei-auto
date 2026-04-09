@echo off
REM ================================================================
REM  SEI Automation - Rodar interface grafica (modo desenvolvimento)
REM ================================================================
cd /d "%~dp0"

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [AVISO] venv nao encontrado. Rodando com Python global.
)

python main_gui.py
if errorlevel 1 pause
