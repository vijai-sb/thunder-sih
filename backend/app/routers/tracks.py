"""Phase 2 routes — additive. Phase 1 /cells etc. unchanged."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..models.schemas import RadarGridCell
from ..services import tracking
from ..sim import engine

router = APIRouter(tags=["nowcast-map"])


@router.get("/tracks")
def get_tracks():
    tracks = tracking.get_tracks()
    return {
        "tracks": tracks,
        "count": len(tracks),
        "scenario_id": engine.get_scenario_id(),
        "tick": engine.get_tick(),
        "horizons_min": tracking.FORECAST_HORIZONS,
        "is_mock": True,
        "note": "Prototype simulated nowcast — constant-velocity extrapolation, not calibrated",
    }


@router.get("/radar-grid")
def get_radar_grid(
    n: int = Query(7, ge=3, le=11),
    step_deg: float = Query(0.05, ge=0.02, le=0.15),
):
    raw = engine.gen_radar_grid(n=n, step_deg=step_deg)
    cells = [RadarGridCell(**c) for c in raw]
    return {
        "cells": cells,
        "count": len(cells),
        "n": n,
        "step_deg": step_deg,
        "scenario_id": engine.get_scenario_id(),
        "tick": engine.get_tick(),
        "is_mock": True,
        "note": "SIMULATED RADAR — deterministic heat representation, not an IMD feed",
    }
