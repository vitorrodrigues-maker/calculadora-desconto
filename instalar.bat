@echo off
chcp 65001 >nul 2>&1
title Calculadora de Desconto - Instalacao
echo.
echo ============================================
echo   Instalando Calculadora de Desconto...
echo ============================================
echo.

cd /d "%~dp0"
echo   Pasta: %CD%
echo.

echo [1/5] Verificando Python...
python --version
if errorlevel 1 (
    echo.
    echo   ERRO: Python nao encontrado!
    echo   Instale em: https://www.python.org/downloads/
    echo   IMPORTANTE: Marque "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
echo.

echo [2/5] Verificando configuracao...
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo   Arquivo .env criado a partir do exemplo.
        echo   ATENCAO: Edite o arquivo .env com suas credenciais
        echo   do Metabase antes de usar a calculadora.
        echo.
        notepad .env
        echo   Salve o .env e pressione ENTER aqui para continuar...
        pause >nul
    )
)
echo   Configuracao OK
echo.

echo [3/5] Instalando dependencias (pode levar alguns minutos)...
echo   Atualizando pip...
python -m pip install --upgrade pip
echo.
echo   Instalando Flask, requests, etc...
python -m pip install -r requirements.txt
echo.
echo   Instalando PyInstaller...
python -m pip install pyinstaller
echo.
echo   Dependencias OK
echo.

echo [4/5] Gerando executavel (pode levar 2-3 minutos)...
if exist build rmdir /s /q build >nul 2>&1
if exist dist rmdir /s /q dist >nul 2>&1
python -m PyInstaller calculadora.spec --noconfirm --clean
echo.

if exist "dist\CalculadoraDesconto.exe" (
    echo [5/5] Criando atalho na Area de Trabalho...
    echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\atalho.vbs"
    echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Calculadora de Desconto.lnk" >> "%TEMP%\atalho.vbs"
    echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\atalho.vbs"
    echo oLink.TargetPath = "%CD%\dist\CalculadoraDesconto.exe" >> "%TEMP%\atalho.vbs"
    echo oLink.WorkingDirectory = "%CD%\dist" >> "%TEMP%\atalho.vbs"
    echo oLink.Description = "Calculadora de Aprovacao de Desconto" >> "%TEMP%\atalho.vbs"
    echo oLink.Save >> "%TEMP%\atalho.vbs"
    cscript /nologo "%TEMP%\atalho.vbs"
    del "%TEMP%\atalho.vbs"
    echo   Atalho criado na Area de Trabalho!
    echo.
    echo ============================================
    echo   INSTALACAO CONCLUIDA!
    echo.
    echo   Um atalho "Calculadora de Desconto" foi
    echo   criado na sua Area de Trabalho.
    echo   Clique 2x nele para usar!
    echo ============================================
) else (
    echo ============================================
    echo   ERRO na instalacao.
    echo   Tente executar como Administrador:
    echo   Botao direito ^> Executar como administrador
    echo ============================================
)

echo.
pause
