"""System routes: health, scenarios, source health + outage simulation."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..adapters import factory
from ..models.schemas import DataSourceMeta, ScenarioInfo
from ..sim import engine

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "storm-nowcast-phase1",
        "data_mode": "mock",
        "is_mock": True,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "note": "SIMULATED DEMO DATA — not IMD live",
    }


@router.get("/scenarios")
def list_scenarios():
    return {"scenarios": engine.list_scenarios(), "current": engine.current_info(), "is_mock": True}


@router.get("/scenario")
def get_scenario():
    info = engine.current_info()
    sc = engine.scenario_def()
    return ScenarioInfo(
        scenario_id=info["scenario_id"],
        display_name=sc["display_name"],
        description=sc["description"],
        tick=info["tick"],
        sim_time_utc=info["sim_time_utc"],
        is_mock=True,
    )


@router.post("/scenario/{scenario_id}")
def set_scenario(scenario_id: str):
    try:
        engine.set_scenario(scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return get_scenario()


@router.post("/scenario-advance")
def advance(steps: int = 1):
    if steps < 1 or steps > 24:
        raise HTTPException(status_code=400, detail="steps must be 1..24")
    engine.advance_tick(steps)
    return get_scenario()


@router.post("/scenario-reset")
def reset():
    engine.reset_clock()
    return get_scenario()


@router.get("/sources")
def get_sources():
    out: list[DataSourceMeta] = []
    for a in factory.all_adapters():
        offline = engine.is_offline(a.source_id)
        out.append(
            DataSourceMeta(
                source_id=a.source_id,
                display_name=a.display_name,
                connected=not offline,
                status="offline" if offline else "ok",
                last_update_utc=datetime.now(timezone.utc).isoformat(),
                latency_sec=a.latency_sec,
                missing_data=offline,
                message="Simulated outage (fallback demo)" if offline else "Simulated feed OK",
            )
        )
    return {"sources": out, "is_mock": True}


@router.post("/sources/{source_id}/offline")
def force_offline(source_id: str):
    valid = {"radar", "satellite", "lightning", "nwp"}
    if source_id not in valid:
        raise HTTPException(status_code=400, detail=f"unknown source '{source_id}'")
    engine.set_source_offline(source_id, True)
    return {"source_id": source_id, "connected": False, "is_mock": True}


@router.post("/sources/{source_id}/online")
def force_online(source_id: str):
    valid = {"radar", "satellite", "lightning", "nwp"}
    if source_id not in valid:
        raise HTTPException(status_code=400, detail=f"unknown source '{source_id}'")
    engine.set_source_offline(source_id, False)
    return {"source_id": source_id, "connected": True, "is_mock": True}
