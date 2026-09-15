"""Monta os dados do painel (setores, leads, calendário) como dict puro —
usado pelo endpoint GET /api/dashboard do web_server.py. O painel em si é o
app React em frontend/ (antes era HTML gerado por template Python direto
aqui; ver histórico do etapa4_dashboard.py, removido quando o front virou
React+shadcn+ReUI).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from prospector import config, db
from prospector.models import PROSPECTAVEL_STATUSES

CALENDAR_HISTORY_DAYS = 180


def _pending_siglas(lead: dict) -> list[str]:
    return sorted({l["sigla"] for l in lead["licenses"] if l.get("status") in PROSPECTAVEL_STATUSES})


def _lead_to_row(lead: dict) -> dict:
    pending = [
        {
            "sigla": l["sigla"],
            "status": l["status"],
            "nome": l["nome_comercial"],
            "validade": l.get("data_validade") or "",
        }
        for l in lead["licenses"]
        if l.get("status") in PROSPECTAVEL_STATUSES
    ]
    return {
        "nome": lead["name"],
        "cnpj": lead["cnpj"],
        "bairro": lead.get("bairro") or "",
        "segmento": lead["segment"],
        "instagram": lead.get("instagram") or "",
        "dono": lead.get("owner_name") or "",
        "data": lead.get("run_date") or "",
        "pendentes": pending,
        "siglas": _pending_siglas(lead),
    }


def build_dashboard_data(db_path: Path) -> dict:
    with db.connect(db_path) as conn:
        latest_run_id = db.get_latest_run_id(conn)
        current_raw = db.fetch_leads_for_run(conn, latest_run_id) if latest_run_id else []
        history_raw = db.fetch_leads_before_run(conn, latest_run_id) if latest_run_id else []
        calendar_raw = db.fetch_recent_leads(conn, days=CALENDAR_HISTORY_DAYS)
        qualified_raw = db.fetch_qualified_leads_by_segment(conn)
        qualified_today_raw = db.fetch_qualified_leads_today(conn)

    current = [_lead_to_row(l) for l in current_raw]
    history = [_lead_to_row(l) for l in history_raw]
    qualified_rows = [_lead_to_row(l) for l in qualified_raw]
    qualified_today_rows = [_lead_to_row(l) for l in qualified_today_raw]

    # cor por setor: hue varrendo o arco laranja->verde->teal da marca CicloJr
    # (não o círculo inteiro), mesma ordem sempre (todos os setores
    # conhecidos, não só os com lead), alternando claro/escuro pra diferenciar
    # mais os setores dentro de um arco de hue mais estreito.
    all_segment_names = sorted(config.load_segments().keys())
    n_segments = max(len(all_segment_names), 1)
    hue_start, hue_end = 25, 195  # laranja -> verde -> teal
    segment_colors: dict[str, str] = {}
    for i, seg in enumerate(all_segment_names):
        span = hue_end - hue_start
        hue = hue_start + (i * span / (n_segments - 1) if n_segments > 1 else span / 2)
        lightness, chroma = (0.62, 0.15) if i % 2 == 0 else (0.47, 0.12)
        segment_colors[seg] = f"oklch({lightness} {chroma} {round(hue, 1)}deg)"

    qualified_by_segment: dict[str, list[dict]] = defaultdict(list)
    for row in qualified_rows:
        qualified_by_segment[row["segmento"]].append(row)

    segment_summary = []
    for seg in all_segment_names:
        rows = qualified_by_segment.get(seg, [])
        bairro_counts = Counter(r["bairro"] or "(sem bairro)" for r in rows)
        segment_summary.append(
            {
                "segmento": seg,
                "total": len(rows),
                "cor": segment_colors[seg],
                "bairros": [{"bairro": b, "total": c} for b, c in bairro_counts.most_common()],
            }
        )
    segment_summary.sort(key=lambda s: s["total"], reverse=True)

    qualified_by_segment_today: dict[str, list[dict]] = defaultdict(list)
    for row in qualified_today_rows:
        qualified_by_segment_today[row["segmento"]].append(row)
    segment_summary_today = [
        {"segmento": seg, "total": len(qualified_by_segment_today.get(seg, [])), "cor": segment_colors[seg]}
        for seg in all_segment_names
    ]
    segment_summary_today.sort(key=lambda s: s["total"], reverse=True)

    by_date: dict[str, list[dict]] = defaultdict(list)
    for lead in calendar_raw:
        by_date[lead["run_date"]].append(_lead_to_row(lead))

    run_label = latest_run_id.replace("T", " ") if latest_run_id else None

    return {
        "run_label": run_label,
        "current": current,
        "history": history,
        "calendar_by_date": by_date,
        "segment_summary": segment_summary,
        "segment_summary_today": segment_summary_today,
        "qualified_by_segment": qualified_by_segment,
        "total_qualified_today": len(qualified_today_rows),
    }
