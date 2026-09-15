from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

from prospector.models import LicenseStatus, QualifiedLead

SCHEMA = """
CREATE TABLE IF NOT EXISTS deliveries (
    cnpj TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    segment TEXT NOT NULL,
    instagram TEXT,
    owner_name TEXT,
    licenses_json TEXT NOT NULL,
    first_delivered_at TEXT NOT NULL,
    last_delivered_at TEXT NOT NULL
);

-- Uma linha por lead ENTREGUE em uma execução. `run_id` identifica a
-- execução (não o dia): rodar o sistema de novo — mesmo no mesmo dia —
-- cria um run_id novo, e os leads da execução anterior passam a fazer
-- parte do histórico automaticamente (não existe mais "hoje" fixo).
CREATE TABLE IF NOT EXISTS daily_leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    run_date TEXT NOT NULL,
    segment TEXT NOT NULL,
    bairro TEXT,
    cnpj TEXT NOT NULL,
    name TEXT NOT NULL,
    instagram TEXT,
    owner_name TEXT,
    licenses_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_daily_leads_run_date ON daily_leads(run_date);

-- Registra TODO CNPJ checado no Portal SEUMA (qualificado ou não), pra evitar
-- reconsultar o mesmo CNPJ toda vez que o sistema roda mais de uma vez por
-- semana. A maioria dos CNPJs não está no SEUMA (not_found) — sem esse
-- cache, cada execução reconsultaria os mesmos "not_found" do começo do
-- extrato, desperdiçando tempo.
CREATE TABLE IF NOT EXISTS checked_cnpj (
    cnpj TEXT NOT NULL,
    segment TEXT NOT NULL,
    bairro TEXT,
    result TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    PRIMARY KEY (cnpj, segment)
);

CREATE INDEX IF NOT EXISTS idx_checked_cnpj_checked_at ON checked_cnpj(checked_at);
"""


@contextmanager
def connect(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """Adiciona colunas novas a bancos criados antes delas existirem (sqlite
    não tem "ADD COLUMN IF NOT EXISTS", então checa o schema primeiro)."""
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(daily_leads)")}
    if "run_id" not in cols:
        # linhas antigas (de antes do conceito de execução) usam o próprio
        # run_date como run_id, pra continuar aparecendo no histórico.
        conn.execute("ALTER TABLE daily_leads ADD COLUMN run_id TEXT")
        conn.execute("UPDATE daily_leads SET run_id = run_date WHERE run_id IS NULL")
    if "bairro" not in cols:
        conn.execute("ALTER TABLE daily_leads ADD COLUMN bairro TEXT")
    if "owner_name" not in cols:
        conn.execute("ALTER TABLE daily_leads ADD COLUMN owner_name TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_leads_run_id ON daily_leads(run_id)")

    delivery_cols = {row["name"] for row in conn.execute("PRAGMA table_info(deliveries)")}
    if "owner_name" not in delivery_cols:
        conn.execute("ALTER TABLE deliveries ADD COLUMN owner_name TEXT")

    checked_cols = {row["name"] for row in conn.execute("PRAGMA table_info(checked_cnpj)")}
    if "bairro" not in checked_cols:
        conn.execute("ALTER TABLE checked_cnpj ADD COLUMN bairro TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_checked_cnpj_checked_at ON checked_cnpj(checked_at)")


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def _licenses_snapshot(lead: QualifiedLead) -> dict:
    return {l.sigla: l.status for l in lead.licenses}


def get_last_delivered_snapshot(conn: sqlite3.Connection, cnpj: str) -> dict | None:
    row = conn.execute(
        "SELECT licenses_json FROM deliveries WHERE cnpj = ?", (cnpj,)
    ).fetchone()
    if row is None:
        return None
    return json.loads(row["licenses_json"])


def should_deliver(conn: sqlite3.Connection, lead: QualifiedLead) -> bool:
    """Regra de dedup: só reentrega se alguma licença mudou de status desde a última entrega."""
    last = get_last_delivered_snapshot(conn, lead.cnpj)
    if last is None:
        return True
    return last != _licenses_snapshot(lead)


def record_delivery(conn: sqlite3.Connection, lead: QualifiedLead, run_id: str, run_date: date) -> None:
    snapshot_json = json.dumps(_licenses_snapshot(lead), ensure_ascii=False)
    licenses_full_json = json.dumps(
        [l.__dict__ for l in lead.licenses], ensure_ascii=False
    )
    now = run_date.isoformat()

    conn.execute(
        """
        INSERT INTO deliveries (cnpj, name, segment, instagram, owner_name, licenses_json, first_delivered_at, last_delivered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(cnpj) DO UPDATE SET
            name=excluded.name,
            segment=excluded.segment,
            instagram=excluded.instagram,
            owner_name=excluded.owner_name,
            licenses_json=excluded.licenses_json,
            last_delivered_at=excluded.last_delivered_at
        """,
        (lead.cnpj, lead.name, lead.segment, lead.instagram, lead.owner_name, snapshot_json, now, now),
    )

    conn.execute(
        """
        INSERT INTO daily_leads (run_id, run_date, segment, bairro, cnpj, name, instagram, owner_name, licenses_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, now, lead.segment, lead.bairro, lead.cnpj, lead.name, lead.instagram, lead.owner_name, licenses_full_json, now),
    )


def get_latest_run_id(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT run_id FROM daily_leads ORDER BY id DESC LIMIT 1").fetchone()
    return row["run_id"] if row else None


def fetch_leads_for_run(conn: sqlite3.Connection, run_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM daily_leads WHERE run_id = ? ORDER BY segment, name",
        (run_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def fetch_leads_before_run(conn: sqlite3.Connection, run_id: str, limit: int = 500) -> list[dict]:
    """Histórico: tudo que não é da execução mais recente, mais nova primeiro."""
    rows = conn.execute(
        """
        SELECT * FROM daily_leads
        WHERE run_id != ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (run_id, limit),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def fetch_recent_leads(conn: sqlite3.Connection, days: int = 30) -> list[dict]:
    """Todos os leads entregues nos últimos `days` dias (qualquer execução),
    usado pra montar a visão de calendário — inclui `run_date` em cada linha."""
    rows = conn.execute(
        """
        SELECT * FROM daily_leads
        WHERE run_date >= date('now', ?)
        ORDER BY run_date DESC, segment, name
        """,
        (f"-{days} days",),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_recently_checked_cnpjs(conn: sqlite3.Connection, segment: str, days: int) -> set[str]:
    """CNPJs já checados no SEUMA para este segmento nos últimos `days` dias
    (qualquer resultado — qualificado, não qualificado, not_found, ambíguo).
    Usado para pular reconsulta em execuções repetidas na mesma semana."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT cnpj FROM checked_cnpj WHERE segment = ? AND checked_at >= ?",
        (segment, cutoff),
    ).fetchall()
    return {r["cnpj"] for r in rows}


def record_check(
    conn: sqlite3.Connection, cnpj: str, segment: str, result: str, checked_at: date, bairro: str = ""
) -> None:
    conn.execute(
        """
        INSERT INTO checked_cnpj (cnpj, segment, bairro, result, checked_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(cnpj, segment) DO UPDATE SET
            bairro = excluded.bairro,
            result = excluded.result,
            checked_at = excluded.checked_at
        """,
        (cnpj, segment, bairro, result, checked_at.isoformat()),
    )


def fetch_qualified_leads_today(conn: sqlite3.Connection) -> list[dict]:
    """Uma linha por CNPJ qualificado/entregue HOJE (a mais recente, se
    entregue mais de uma vez no dia) — alimenta o gráfico de rosca da página
    inicial, que mostra só o dia (diferente da aba "Setores", que é o total
    geral — ver fetch_qualified_leads_by_segment)."""
    today = date.today().isoformat()
    rows = conn.execute(
        """
        SELECT dl.* FROM daily_leads dl
        INNER JOIN (
            SELECT cnpj, MAX(id) AS max_id FROM daily_leads WHERE run_date = ? GROUP BY cnpj
        ) latest ON dl.cnpj = latest.cnpj AND dl.id = latest.max_id
        WHERE dl.run_date = ?
        ORDER BY dl.segment, dl.name
        """,
        (today, today),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def fetch_qualified_leads_by_segment(conn: sqlite3.Connection) -> list[dict]:
    """Uma linha por CNPJ já qualificado/entregue alguma vez (a mais recente
    em daily_leads pra esse CNPJ, com bairro/instagram/licenças atualizados)
    — alimenta o dashboard de "Setores" (quantos qualificados por setor e por
    bairro). Usa daily_leads (tem bairro) em vez de deliveries (não tem)."""
    rows = conn.execute(
        """
        SELECT dl.* FROM daily_leads dl
        INNER JOIN (
            SELECT cnpj, MAX(id) AS max_id FROM daily_leads GROUP BY cnpj
        ) latest ON dl.cnpj = latest.cnpj AND dl.id = latest.max_id
        ORDER BY dl.segment, dl.name
        """
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["licenses"] = json.loads(d.pop("licenses_json"))
    return d
