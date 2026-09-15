@echo off
cd /d "%~dp0"
echo ==========================================
echo   Prospector - Configuracao inicial
echo ==========================================
echo.
echo Isso so precisa ser feito UMA VEZ nesta maquina.
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERRO] Python nao foi encontrado.
    echo.
    echo Baixe em https://www.python.org/downloads/ ^(versao 3.12 ou mais nova^)
    echo e marque a opcao "Add python.exe to PATH" durante a instalacao.
    echo Depois de instalar, feche esta janela e de dois cliques aqui de novo.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Criando ambiente Python...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Nao consegui criar o ambiente Python. Veja a mensagem acima.
        pause
        exit /b 1
    )
)

echo Instalando dependencias do Python (pode demorar um pouco)...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha instalando as dependencias. Veja a mensagem acima.
    pause
    exit /b 1
)

echo Baixando o navegador do Playwright (Chromium, so na primeira vez)...
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 (
    echo [ERRO] Falha baixando o Chromium. Veja a mensagem acima.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Tudo pronto!
echo A partir de agora, use sempre o iniciar_painel.bat pra abrir o sistema.
echo ==========================================
pause
