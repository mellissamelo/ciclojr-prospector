"""Servidor web local para rodar o pipeline direto do painel (o app React em
frontend/, buildado em frontend/dist e servido daqui): escolhe setor + bairro
e clica em "Prospectar" na própria página, sem precisar abrir uma janela
separada (app_gui.py continua existindo como alternativa via desktop, pra
quem preferir).

Uso: dê duplo-clique em iniciar_painel.bat (ou rode
`python scripts/iniciar_painel.py`) — abre o navegador em
http://127.0.0.1:5000/.
"""
from __future__ import annotations

import logging
import threading

from flask import Flask, jsonify, request, send_from_directory

from prospector import config, db, pipeline, rf_source
from prospector.dashboard_data import build_dashboard_data

log = logging.getLogger(__name__)

app = Flask(__name__)

_lock = threading.Lock()
_state = {
    "running": False,
    "log": [],
    "segment": None,
    "bairro": None,
    "run_seq": 0,
    "checked_count": 0,
    "total_count": 0,
    "delivered_count": 0,
}
_stop_event = threading.Event()

_MAX_LOG_LINES = 500


class _ListLogHandler(logging.Handler):
    """Acumula as linhas de log da execução em memória, pro painel puxar via
    polling (GET /api/status) — mesma ideia da QueueLogHandler do app_gui.py,
    só que sem fila/tkinter, direto numa lista compartilhada."""

    def emit(self, record: logging.LogRecord) -> None:
        line = self.format(record)
        with _lock:
            _state["log"].append(line)
            if len(_state["log"]) > _MAX_LOG_LINES:
                del _state["log"][: len(_state["log"]) - _MAX_LOG_LINES]


_handler = _ListLogHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%H:%M:%S"))
logging.getLogger("prospector").addHandler(_handler)
logging.getLogger("prospector").setLevel(logging.INFO)


def _on_progress(checked: int, total: int, delivered: int) -> None:
    with _lock:
        _state["checked_count"] = checked
        _state["total_count"] = total
        _state["delivered_count"] = delivered


def _run_pipeline(segment: str, bairro: str | None) -> None:
    try:
        pipeline.run_daily(
            segment, bairro=bairro, should_stop=_stop_event.is_set, on_progress=_on_progress
        )
    except Exception:
        log.exception("Erro na execução")
    finally:
        with _lock:
            _state["running"] = False


@app.get("/api/segments")
def api_segments():
    rf_sources = config.load_rf_sources()
    out = {}
    for segment, info in rf_sources.items():
        csv_path = config.ROOT_DIR / info["csv"]
        out[segment] = rf_source.list_bairros(csv_path)
    return jsonify(out)


@app.get("/api/dashboard")
def api_dashboard():
    settings = config.load_settings()
    return jsonify(build_dashboard_data(settings.db_path))


@app.post("/api/run")
def api_run():
    data = request.get_json(force=True, silent=True) or {}
    segment = (data.get("segment") or "").strip()
    bairro = (data.get("bairro") or "").strip() or None

    with _lock:
        if _state["running"]:
            return jsonify({"ok": False, "error": "Já tem uma prospecção rodando."}), 409

        segments = config.load_segments()
        rf_sources = config.load_rf_sources()
        if segment not in segments or segment not in rf_sources:
            return jsonify({"ok": False, "error": f"Setor inválido: {segment!r}"}), 400

        _stop_event.clear()
        _state["running"] = True
        _state["log"] = []
        _state["segment"] = segment
        _state["bairro"] = bairro
        _state["run_seq"] += 1
        _state["checked_count"] = 0
        _state["total_count"] = 0
        _state["delivered_count"] = 0

    threading.Thread(target=_run_pipeline, args=(segment, bairro), daemon=True).start()
    return jsonify({"ok": True})


@app.post("/api/stop")
def api_stop():
    _stop_event.set()
    return jsonify({"ok": True})


@app.get("/api/status")
def api_status():
    with _lock:
        return jsonify(dict(_state))


@app.get("/")
@app.get("/<path:path>")
def spa(path: str = "index.html"):
    """Serve o app React buildado (frontend/dist). Qualquer rota que não seja
    um arquivo estático real cai no index.html — o roteamento de abas é todo
    client-side (não há rotas de servidor além de /api/*)."""
    settings = config.load_settings()
    dist_dir = settings.frontend_dist_dir
    if not dist_dir.exists():
        return (
            "Painel não buildado ainda. Rode `npm install && npm run build` "
            "dentro da pasta frontend/ (ou use o iniciar_painel.bat, que faz "
            "isso automaticamente).",
            503,
        )
    candidate = dist_dir / path
    if path != "index.html" and candidate.is_file():
        return send_from_directory(dist_dir, path)
    return send_from_directory(dist_dir, "index.html")


def main() -> None:
    settings = config.load_settings()
    db.init_db(settings.db_path)
    # threaded=True é essencial aqui: sem isso o servidor de dev do Flask
    # atende um pedido HTTP por vez, então o polling de /api/status (a cada
    # 1.5s) podia atrasar/engasgar o clique em "Parar" (POST /api/stop) até
    # a próxima folga — com várias abas ou polling mais frequente, dava pra
    # sentir esse atraso como "o botão não funciona".
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
