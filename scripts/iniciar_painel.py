#!/usr/bin/env python
"""Sobe o servidor local do painel e abre o navegador em
http://127.0.0.1:5000/ — dali dá pra escolher setor + bairro e clicar
"Prospectar" direto na página, sem terminal nem janela separada.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from prospector import web_server  # noqa: E402

URL = "http://127.0.0.1:5000/"

_NPM_FALLBACKS = [
    r"C:\Program Files\nodejs\npm.cmd",
    r"C:\Program Files (x86)\nodejs\npm.cmd",
]


def _find_npm() -> str | None:
    found = shutil.which("npm")
    if found:
        return found
    for candidate in _NPM_FALLBACKS:
        if Path(candidate).exists():
            return candidate
    return None


def _ensure_frontend_built() -> None:
    """O painel é o app React em frontend/, buildado uma vez pra
    frontend/dist e servido estático pelo Flask — sem build, não tem o que
    servir. Builda sozinho na primeira vez (ou se alguém apagar dist/),
    igual ao Chromium do Playwright: só incomoda uma vez."""
    frontend_dir = ROOT_DIR / "frontend"
    dist_index = frontend_dir / "dist" / "index.html"
    if dist_index.exists():
        return

    npm = _find_npm()
    if not npm:
        print(
            "Painel (frontend) ainda não foi buildado e o Node.js/npm não foi "
            "encontrado nesta máquina. Instale o Node.js (https://nodejs.org/) "
            "e rode de novo, ou rode manualmente:\n"
            "  cd frontend && npm install && npm run build"
        )
        raise SystemExit(1)

    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("Preparando o painel pela primeira vez (instalando dependências)...")
        subprocess.run([npm, "install"], cwd=frontend_dir, check=True, shell=True)

    print("Preparando o painel pela primeira vez (build)...")
    subprocess.run([npm, "run", "build"], cwd=frontend_dir, check=True, shell=True)


def _ensure_playwright_browser() -> None:
    """Confirma que o Chromium do Playwright está instalado antes de subir o
    servidor — se não estiver (ex.: máquina nova, ou instalação incompleta),
    a checagem no SEUMA falhava direto sem avisar nada de útil na tela."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return
    except Exception:
        pass

    print("Chromium do Playwright ausente/incompleto — instalando (só acontece uma vez)...")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)


def main() -> None:
    _ensure_frontend_built()
    _ensure_playwright_browser()
    threading.Timer(1.0, lambda: webbrowser.open(URL)).start()
    web_server.main()


if __name__ == "__main__":
    main()
