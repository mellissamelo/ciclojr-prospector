#!/usr/bin/env python
"""App de mesa (tkinter, já vem com o Python — nada pra instalar) pra rodar o
sistema sem terminal: escolhe setor + bairro, clica "Prospectar" e acompanha
o progresso na hora. Substitui o prompt de texto do rodar_hoje.bat por uma
telinha de verdade.

Uso: dê duplo-clique em abrir_app.bat (ou rode `pythonw scripts/app_gui.py`
pra não abrir uma janela de terminal atrás).
"""
from __future__ import annotations

import logging
import queue
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import Tk, StringVar, END, DISABLED, NORMAL
from tkinter import ttk, scrolledtext

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prospector import config, pipeline, rf_source  # noqa: E402

TODOS_BAIRROS = "(Todos os bairros)"


class QueueLogHandler(logging.Handler):
    """Manda cada linha de log pra uma fila — o loop do tkinter lê essa fila
    periodicamente (não dá pra mexer em widget de outra thread direto)."""

    def __init__(self, q: queue.Queue):
        super().__init__()
        self.q = q

    def emit(self, record: logging.LogRecord) -> None:
        self.q.put(self.format(record))


def _bairros_do_segmento(segment: str) -> list[str]:
    try:
        rf_sources = config.load_rf_sources()
        csv_path = config.ROOT_DIR / rf_sources[segment]["csv"]
        return rf_source.list_bairros(csv_path)
    except Exception:
        return []


class App:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("Prospector — Leads de Licenças (Fortaleza-CE)")
        self.root.geometry("640x520")
        self.root.minsize(560, 420)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.running = False
        self.stop_event = threading.Event()

        self._build_ui()
        self._setup_logging()
        self._poll_log_queue()

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}

        form = ttk.Frame(self.root)
        form.pack(fill="x", **pad)

        ttk.Label(form, text="Setor:").grid(row=0, column=0, sticky="w")
        self.segment_var = StringVar()
        rf_sources = config.load_rf_sources()
        segments_prontos = list(rf_sources.keys())
        self.segment_combo = ttk.Combobox(
            form, textvariable=self.segment_var, values=segments_prontos, state="readonly", width=30
        )
        if segments_prontos:
            self.segment_combo.current(0)
        self.segment_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.segment_combo.bind("<<ComboboxSelected>>", lambda e: self._atualizar_bairros())

        ttk.Label(form, text="Bairro:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.bairro_var = StringVar(value=TODOS_BAIRROS)
        self.bairro_combo = ttk.Combobox(form, textvariable=self.bairro_var, state="readonly", width=30)
        self.bairro_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))

        form.columnconfigure(1, weight=1)

        btn_row = ttk.Frame(self.root)
        btn_row.pack(fill="x", **pad)

        self.prospectar_btn = ttk.Button(btn_row, text="▶ Prospectar", command=self._on_prospectar)
        self.prospectar_btn.pack(side="left")

        self.parar_btn = ttk.Button(btn_row, text="■ Parar", command=self._on_parar, state=DISABLED)
        self.parar_btn.pack(side="left", padx=(8, 0))

        self.painel_btn = ttk.Button(btn_row, text="Abrir painel", command=self._abrir_painel)
        self.painel_btn.pack(side="right")

        self.status_var = StringVar(value="Pronto.")
        ttk.Label(self.root, textvariable=self.status_var, foreground="#2f6b4f").pack(
            anchor="w", padx=12
        )

        self.log_box = scrolledtext.ScrolledText(self.root, height=20, state=DISABLED, wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._atualizar_bairros()

    def _atualizar_bairros(self) -> None:
        segment = self.segment_var.get()
        bairros = [TODOS_BAIRROS] + _bairros_do_segmento(segment)
        self.bairro_combo["values"] = bairros
        self.bairro_var.set(TODOS_BAIRROS)

    def _setup_logging(self) -> None:
        handler = QueueLogHandler(self.log_queue)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%H:%M:%S"))
        logging.getLogger("prospector").addHandler(handler)
        logging.getLogger("prospector").setLevel(logging.INFO)

    def _poll_log_queue(self) -> None:
        try:
            while True:
                line = self.log_queue.get_nowait()
                self.log_box.configure(state=NORMAL)
                self.log_box.insert(END, line + "\n")
                self.log_box.see(END)
                self.log_box.configure(state=DISABLED)
        except queue.Empty:
            pass
        self.root.after(200, self._poll_log_queue)

    def _on_prospectar(self) -> None:
        if self.running:
            return
        segment = self.segment_var.get()
        if not segment:
            self.status_var.set("Escolha um setor primeiro.")
            return
        bairro = self.bairro_var.get()
        bairro = None if bairro in ("", TODOS_BAIRROS) else bairro

        self.running = True
        self.stop_event.clear()
        self.prospectar_btn.configure(state=DISABLED)
        self.parar_btn.configure(state=NORMAL)
        self.segment_combo.configure(state=DISABLED)
        self.bairro_combo.configure(state=DISABLED)
        self.status_var.set(f"Rodando: {segment}" + (f" / {bairro}" if bairro else ""))

        thread = threading.Thread(target=self._run_pipeline, args=(segment, bairro), daemon=True)
        thread.start()

    def _run_pipeline(self, segment: str, bairro: str | None) -> None:
        try:
            pipeline.run_daily(segment, bairro=bairro, should_stop=self.stop_event.is_set)
            self.status_var.set("Concluído.")
        except Exception as e:
            logging.getLogger("prospector").exception("Erro na execução: %s", e)
            self.status_var.set(f"Erro: {e}")
        finally:
            self.running = False
            self.root.after(0, self._on_pipeline_finished)

    def _on_pipeline_finished(self) -> None:
        self.prospectar_btn.configure(state=NORMAL)
        self.parar_btn.configure(state=DISABLED)
        self.segment_combo.configure(state="readonly")
        self.bairro_combo.configure(state="readonly")

    def _on_parar(self) -> None:
        self.stop_event.set()
        self.status_var.set("Parando (termina o lead atual e para)...")
        self.parar_btn.configure(state=DISABLED)

    def _abrir_painel(self) -> None:
        # o painel agora é o app React servido pelo Flask (ver web_server.py)
        # — precisa do iniciar_painel.bat rodando, não é mais um arquivo
        # estático que dá pra abrir direto.
        webbrowser.open("http://127.0.0.1:5000/")
        self.status_var.set(
            "Abrindo painel — se a página não carregar, rode o iniciar_painel.bat também."
        )


def main() -> None:
    root = Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
