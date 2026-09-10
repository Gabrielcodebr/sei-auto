@echo off
REM Gera o SeiAuto.exe a partir do codigo-fonte atual.
REM Pode ser executado de qualquer lugar (duplo-clique resolve).

cd /d "%~dp0"

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [AVISO] venv nao encontrado. Usando Python global.
)

echo.
echo === Gerando SeiAuto.exe ===
echo.

python -m PyInstaller --onefile --noconsole --name SeiAuto ^
  --hidden-import win32com ^
  --hidden-import pythoncom ^
  --hidden-import pywintypes ^
  --noconfirm ^
  main_gui.py

if errorlevel 1 (
    echo.
    echo [ERRO] Build falhou. Veja as mensagens acima.
    pause
    exit /b 1
)

echo.
echo === Build concluido: dist\SeiAuto.exe ===
echo.
pause