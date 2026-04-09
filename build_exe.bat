@echo off
REM ================================================================
REM  SEI Automation - Build do executavel
REM ================================================================
REM  Gera SeiAuto.exe na raiz do projeto usando PyInstaller.
REM  Requer: venv ativado + pyinstaller instalado
REM         (pip install -r requirements.txt)
REM ================================================================

cd /d "%~dp0"

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [AVISO] venv\Scripts\activate.bat nao encontrado.
    echo Voce precisa criar o venv primeiro: python -m venv venv
    echo e instalar as dependencias: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Gerando executavel SeiAuto.exe...
echo ============================================
echo.

pyinstaller SeiAuto.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [ERRO] Falha na geracao do executavel.
    pause
    exit /b 1
)

echo.
echo Copiando executavel para a raiz do projeto...
if exist dist\SeiAuto.exe (
    copy /Y dist\SeiAuto.exe SeiAuto.exe >nul
    echo.
    echo ============================================
    echo  SUCESSO! SeiAuto.exe gerado na raiz.
    echo ============================================
    echo.
    echo Voce pode dar duplo-clique em SeiAuto.exe
    echo para rodar a interface grafica.
) else (
    echo [ERRO] dist\SeiAuto.exe nao foi gerado.
    pause
    exit /b 1
)

echo.
pause
