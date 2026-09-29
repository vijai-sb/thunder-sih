"""Phase 4 routes — guided demo + POI dataset. Additive; Phases 1–3 unchanged."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import impact
from ..sim import engine

router = APIRouter(tags=["demo"])

# Simulation stages (NOT forecast times). Deterministic scripted path through
# the developing → intensifying → severe story.
DEMO_PLAN = [
    {"stage": "T+00", "scenario_id": "developing", "tick": 0, "caption": "Developing storm — cells organizing"},
    {"stage": "T+15", "scenario_id": "developing", "tick": 1, "caption": "Radar intensity increasing"},
    {"stage": "T+30", "scenario_id": "developing", "tick": 2, "caption": "Lightning activity increasing"},
    {"stage": "T+45", "scenario_id": "developing", "tick": 3, "caption": "LIGHTNING JUMP detected"},
    {"stage": "T+60", "scenario_id": "developing", "tick": 4, "caption": "HIGH RISK — alerts fire"},
    {"stage": "T+75", "scenario_id": "intensifying", "tick": 3, "caption": "Impact zone expanding"},
    {"stage": "T+90", "scenario_id": "severe-lightning", "tick": 2, "caption": "ALERT ACTIVE — severe event"},
]


class DemoGoto(BaseModel):
    scenario_id: str
    tick: int = 0


@router.get("/demo/plan")
def get_plan():
    return {
        "steps": DEMO_PLAN,
        "count": len(DEMO_PLAN),
        "is_mock": True,
        "note": "Simulation stages for guided demo — not real forecast times",
    }


@router.post("/demo/goto")
def goto_step(body: DemoGoto):
    if body.scenario_id not in engine.SCENARIOS:
        raise HTTPException(status_code=400, detail=f"unknown scenario '{body.scenario_id}'")
    if not (0 <= body.tick <= 12):
        raise HTTPException(status_code=400, detail="tick must be 0..12")
    engine.set_scenario(body.scenario_id)
    if body.tick:
        engine.advance_tick(body.tick)
    info = engine.current_info()
    return {**info, "is_mock": True, "note": "Simulation stage applied — deterministic sim state"}


@router.get("/pois")
def get_pois():
    return {
        "pois": impact.POIS,
        "count": len(impact.POIS),
        "is_mock": True,
        "note": "SIMULATED DEMO INFRASTRUCTURE — invented points, not real sensitive data",
    }
