"""Phase 3 orchestrator — OBSERVE→DETECT→TRACK→PREDICT→EXPLAIN→IMPACT→WARN.

Builds per-cell intelligence from live sim state + tracking + jump + risk
engine + XAI + impact/TTI, then syncs cell-level alerts to SQLite.
Pure reads of engine (no clock mutation) — deterministic per scenario+tick.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..models.schemas import Provenance
from ..sim import engine
from . import alert_store, impact, lightning_jump, risk_engine, tracking, xai


def _prov() -> Provenance:
    return Provenance(
        source="intel",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        is_mock=True,
        is_live=False,
        data_mode="mock",
        scenario_id=engine.get_scenario_id(),
        tick=engine.get_tick(),
        freshness_sec=0.0,
        note="SIMULATED DEMO intelligence — prototype heuristic, not validated",
    )


def _history_with_risk(cell_id: str, tick: int) -> List[dict]:
    pts = []
    for tt in range(max(0, tick - 4), tick + 1):
        cells = {c["cell_id"]: c for c in engine.gen_cells_at(tt)}
        c = cells.get(cell_id)
        if not c:
            continue
        jr = lightning_jump.analyze_cell(cell_id, tt)
        # historical env at that tick (pure)
        m = engine.model_at(c["center_lat"], c["center_lon"], tt)
        s = engine.satellite_at(c["center_lat"], c["center_lon"], tt)
        score = risk_engine.PrototypeFusionRiskEngine().score(
            {
                "dbz": c["max_reflectivity_dbz"], "flash": c["flash_rate_per_min"],
                "jump": jr["jump_detected"], "trend": jr["trend"],
                "cape": m["cape_jkg"], "humidity": m["humidity_pct"],
                "shear": m["shear_ms"], "ctt": s["cloud_top_temp_c"],
            }
        )
        pts.append({"tick": tt, "flash_rate": c["flash_rate_per_min"], "dbz": c["max_reflectivity_dbz"], "risk_score": score, "jump": jr["jump_detected"]})
    return pts


def _trigger_for(jump: bool, trend: str, dbz_trend: str, lightning_risk: str, storm_risk: str) -> str:
    parts = []
    if jump:
        parts.append("Lightning jump")
    if trend == "increasing":
        parts.append("increasing lightning rate")
    if dbz_trend == "increasing":
        parts.append("increasing radar intensity")
    if not parts:
        parts.append("elevated fused signals")
    return " + ".join(parts)


def build_intelligence() -> List[dict]:
    tick = engine.get_tick()
    tracks = {t.cell_id: t for t in tracking.get_tracks()}
    n_missing = len(engine.offline_sources())
    prov = _prov()
    out = []
    for jr in lightning_jump.all_cells():
        cell_id = jr["cell_id"]
        t = tracks.get(cell_id)
        if t is None:
            continue
        assessed = risk_engine.assess_cell(
            cell_id, _dbz_of(cell_id), jr["current_rate"], jr["jump_detected"], jr["trend"], t.growth_trend, n_missing
        )
        env = assessed["env"]
        expl = xai.explain_cell(
            cell_id, _dbz_of(cell_id), jr["current_rate"], jr["rate_of_change"],
            jr["jump_detected"], env["cape_jkg"], env["humidity_pct"], env["shear_ms"], assessed["ctt"],
        )
        tti = impact.time_to_impact(t.current.lat, t.current.lon, t.speed_kmh, t.direction_deg)
        expo = impact.exposure_forecast([{"horizon_min": h.horizon_min, "lat": h.center_lat, "lon": h.center_lon, "radius_km": h.radius_km} for h in t.hazards])
        hist = _history_with_risk(cell_id, tick)
        out.append({
            "cell_id": cell_id,
            "intensity": t.intensity,
            "jump": {**jr, "threshold_note": "Configurable: abs>=2.0/min, rel>=10%, min 6.0/min (prototype)"},
            "risk": {
                "cell_id": cell_id,
                "prototype_score": assessed["prototype_score"],
                "storm_risk": assessed["storm_risk"],
                "lightning_risk": assessed["lightning_risk"],
                "intensification": assessed["intensification"],
                "confidence_label": "Prototype fusion confidence",
                "confidence_pct": assessed["confidence_pct"],
                "engine": risk_engine.ENGINE_NAME,
            },
            "xai": expl,
            "tti": {"cell_id": cell_id, "target_name": tti["target_name"], "minutes": tti["minutes"]},
            "exposure_30": expo[30], "exposure_60": expo[60], "exposure_90": expo[90],
            "history": hist,
            "provenance": prov,
        })
    return out


def _dbz_of(cell_id: str) -> float:
    c = next((x for x in engine.gen_cells_at(engine.get_tick()) if x["cell_id"] == cell_id), None)
    return float(c["max_reflectivity_dbz"]) if c else 0.0


def sync_alerts(intel: List[dict]) -> List[dict]:
    """Generate/persist alerts for high/severe conditions (deterministic IDs)."""
    synced = []
    for ci in intel:
        storm_risk = ci["risk"]["storm_risk"]
        l_risk = ci["risk"]["lightning_risk"]
        jump = ci["jump"]["jump_detected"]
        fire = storm_risk in ("high", "severe") or (jump and l_risk in ("high", "severe"))
        if not fire:
            continue
        t = next((x for x in tracking.get_tracks() if x.cell_id == ci["cell_id"]), None)
        trigger = _trigger_for(jump, ci["jump"]["trend"], t.dbz_trend if t else "steady", l_risk, storm_risk)
        tti_min = ci["tti"]["minutes"]
        sev = storm_risk if storm_risk in ("high", "severe") else l_risk
        exp60 = ci["exposure_60"]
        msg = (
            f"{sev.upper()} lightning/storm risk near {ci['cell_id']} (Prototype Risk Score "
            f"{ci['risk']['prototype_score']}). Trigger: {trigger}. "
            f"Prototype TTI: {tti_min if tti_min is not None else '—'} min. "
            f"Prototype exposure (60-min zone): {exp60['population']} pop, "
            f"{exp60['schools']} schools, {exp60['hospitals']} hospitals. "
            f"[SIMULATED DEMO — not an official IMD warning]"
        )
        alert_id = f"INT-{engine.get_scenario_id()[:3].upper()}-T{engine.get_tick():03d}-{ci['cell_id']}"
        synced.append(alert_store.upsert_active({
            "alert_id": alert_id,
            "cell_id": ci["cell_id"],
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "severity": sev,
            "trigger": trigger,
            "message": msg,
            "impact_min": tti_min,
            "scenario_id": engine.get_scenario_id(),
            "tick": engine.get_tick(),
        }, run_id=engine.get_run_id()))
    # Auto-resolve superseded ACTIVE alerts (older tick same cell, or other
    # scenario) so ACTIVE always reflects the current sim state. History stays
    # visible under ALL. ACK/RESOLVED set by users are never auto-touched
    # except these ACTIVE→RESOLVED transitions.
    current_ids = {a["alert_id"] for a in synced}
    for old in alert_store.list_alerts("ACTIVE"):
        if old["alert_id"] not in current_ids:
            alert_store.set_status(old["alert_id"], "RESOLVED")
    return synced
