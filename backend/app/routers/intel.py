"""Phase 3 routes — additive. Phases 1–2 unchanged."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from ..services import alert_store, intelligence, lightning_jump, risk_engine
from ..sim import engine

router = APIRouter(tags=["intelligence"])


@router.get("/intel/config")
def get_config():
    return {
        "jump_thresholds": lightning_jump.JUMP_CONFIG,
        "risk_weights": risk_engine.WEIGHTS,
        "risk_engine": risk_engine.ENGINE_NAME,
        "is_mock": True,
        "note": "Prototype thresholds/weights — configurable, not scientifically validated",
    }


@router.get("/intel/cells")
def get_intel_cells():
    intel = intelligence.build_intelligence()
    synced = intelligence.sync_alerts(intel)
    return {
        "cells": intel,
        "count": len(intel),
        "alerts_synced": len(synced),
        "scenario_id": engine.get_scenario_id(),
        "tick": engine.get_tick(),
        "is_mock": True,
        "note": "SIMULATED DEMO intelligence — Prototype Fusion Risk Engine, unvalidated",
    }


@router.get("/intel/cells/{cell_id}")
def get_intel_cell(cell_id: str):
    intel = intelligence.build_intelligence()
    intelligence.sync_alerts(intel)
    for ci in intel:
        if ci["cell_id"] == cell_id:
            return {**ci, "is_mock": True}
    raise HTTPException(status_code=404, detail=f"unknown cell '{cell_id}'")


@router.get("/intel/alerts")
def get_intel_alerts(status: Optional[str] = None):
    if status and status.upper() not in ("ACTIVE", "ACKNOWLEDGED", "RESOLVED"):
        raise HTTPException(status_code=400, detail="status must be ACTIVE|ACKNOWLEDGED|RESOLVED")
    # sync first so demo always shows current-tick alerts
    intelligence.sync_alerts(intelligence.build_intelligence())
    alerts = alert_store.list_alerts(status)
    return {"alerts": alerts, "count": len(alerts), "is_mock": True}


@router.post("/intel/alerts/{alert_id}/ack")
def ack_alert(alert_id: str):
    r = alert_store.set_status(alert_id, "ACKNOWLEDGED")
    if r is None:
        raise HTTPException(status_code=404, detail=f"unknown alert '{alert_id}'")
    return r


@router.post("/intel/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str):
    r = alert_store.set_status(alert_id, "RESOLVED")
    if r is None:
        raise HTTPException(status_code=404, detail=f"unknown alert '{alert_id}'")
    return r
