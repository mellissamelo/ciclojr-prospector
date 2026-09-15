@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat

echo ==========================================
echo   Prospector - Leads de Licencas (Fortaleza-CE)
echo ==========================================
echo.
echo Segmentos disponiveis: ver config\rf_sources.yaml (14 setores prontos)
echo.
set /p SEGMENTO="Setor (Enter = Restaurantes): "
if "%SEGMENTO%"=="" set SEGMENTO=Restaurantes

set /p BAIRRO="Bairro de Fortaleza (Enter = todos): "

echo.
if "%BAIRRO%"=="" (
    python scripts\run_daily.py "%SEGMENTO%" --log-level INFO
) else (
    python scripts\run_daily.py "%SEGMENTO%" --bairro "%BAIRRO%" --log-level INFO
)

echo.
echo ==========================================
echo Terminou. Fecha essa janela quando quiser.
echo ==========================================
pause
