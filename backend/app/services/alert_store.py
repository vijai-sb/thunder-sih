"""Phase 3 alert persistence — SQLite via stdlib (no new dependency).

Single alerts table (no second DB system). Deterministic IDs per
scenario+tick+cell so reset restores state. ACK/RESOLVED preserved.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "alerts.db")
DB_PATH = os.path.abspath(DB_PATH)

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
  alert_id TEXT PRIMARY KEY,
  cell_id TEXT NOT NULL,
  created_at_utc TEXT NOT NULL,
  severity TEXT NOT NULL,
  trigger TEXT NOT NULL,
  message TEXT NOT NULL,
  impact_min REAL,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  scenario_id TEXT NOT NULL,
  tick INTEGER NOT NULL,
  is_mock INTEGER NOT NULL DEFAULT 1
);
"""


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute(SCHEMA)
    try:
        c.execute("SELECT run_id FROM alerts LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE alerts ADD COLUMN run_id INTEGER NOT NULL DEFAULT 0")
    c.commit()
    return c


def upsert_active(alert: dict, run_id: int = 0) -> dict:
    """Insert ACTIVE alert. Same-run refresh preserves ACK/RESOLVED; a new
    simulation run (scenario switch/reset) reactivates re-firing alerts."""
    c = _conn()
    try:
        row = c.execute("SELECT status, run_id FROM alerts WHERE alert_id=?", (alert["alert_id"],)).fetchone()
        if row is None:
            c.execute(
                "INSERT INTO alerts (alert_id, cell_id, created_at_utc, severity, trigger, message, impact_min, status, scenario_id, tick, is_mock, run_id)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,1,?)",
                (
                    alert["alert_id"], alert["cell_id"], alert["created_at_utc"], alert["severity"],
                    alert["trigger"], alert["message"], alert.get("impact_min"),
                    "ACTIVE", alert["scenario_id"], alert["tick"], run_id,
                ),
            )
        elif row["run_id"] != run_id:
            c.execute(
                "UPDATE alerts SET severity=?, trigger=?, message=?, impact_min=?, scenario_id=?, tick=?, status='ACTIVE', run_id=?, created_at_utc=? WHERE alert_id=?",
                (alert["severity"], alert["trigger"], alert["message"], alert.get("impact_min"), alert["scenario_id"], alert["tick"], run_id, alert["created_at_utc"], alert["alert_id"]),
            )
        else:
            c.execute(
                "UPDATE alerts SET severity=?, trigger=?, message=?, impact_min=?, scenario_id=?, tick=? WHERE alert_id=?",
                (alert["severity"], alert["trigger"], alert["message"], alert.get("impact_min"), alert["scenario_id"], alert["tick"], alert["alert_id"]),
            )
        c.commit()
        r = c.execute("SELECT * FROM alerts WHERE alert_id=?", (alert["alert_id"],)).fetchone()
        return dict(r)
    finally:
        c.close()


def list_alerts(status: Optional[str] = None) -> List[dict]:
    c = _conn()
    try:
        if status:
            rows = c.execute("SELECT * FROM alerts WHERE status=? ORDER BY created_at_utc DESC", (status.upper(),)).fetchall()
        else:
            rows = c.execute("SELECT * FROM alerts ORDER BY created_at_utc DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        c.close()


def set_status(alert_id: str, status: str) -> Optional[dict]:
    if status.upper() not in ("ACTIVE", "ACKNOWLEDGED", "RESOLVED"):
        raise ValueError("status must be ACTIVE|ACKNOWLEDGED|RESOLVED")
    c = _conn()
    try:
        c.execute("UPDATE alerts SET status=? WHERE alert_id=?", (status.upper(), alert_id))
        c.commit()
        r = c.execute("SELECT * FROM alerts WHERE alert_id=?", (alert_id,)).fetchone()
        return dict(r) if r else None
    finally:
        c.close()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()
