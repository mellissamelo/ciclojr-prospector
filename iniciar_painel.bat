@echo off
cd /d "%~dp0"
echo Painel do Prospector iniciando... NAO FECHE esta janela enquanto estiver usando o painel no navegador.
".venv\Scripts\python.exe" "scripts\iniciar_painel.py"
echo.
echo O servidor parou. Feche esta janela ou de dois cliques em iniciar_painel.bat de novo.
pause
