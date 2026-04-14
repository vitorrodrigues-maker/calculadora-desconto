@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   Build: Calculadora de Desconto (.exe)
echo ============================================
echo.

cd /d "%~dp0"
echo Diretorio: %CD%
echo.

echo [1/3] Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
echo.

echo [2/3] Limpando builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.

echo [3/3] Gerando executavel...
python -m PyInstaller calculadora.spec --noconfirm --clean
echo.

if exist "dist\CalculadoraDesconto.exe" (
    echo ============================================
    echo   BUILD OK!
    echo.
    echo   Executavel gerado em:
    echo   %CD%\dist\CalculadoraDesconto.exe
    echo ============================================
    echo.
    echo   Envie esse arquivo para o colaborador.
    echo   Ele so precisa clicar 2x para usar.
) else (
    echo ============================================
    echo   ERRO no build. Verifique os logs acima.
    echo ============================================
)

echo.
pause
