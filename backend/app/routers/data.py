"""Data routes: observations, fused state, cells, alerts, prediction (heuristic)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import (
    Alert,
    Location,
    Prediction,
    Provenance,
    StormCell,
    risk_from_prob,
)
from ..services import fusion
from ..sim import engine

router = APIRouter(tags=["data"])

DEFAULT_LAT = 28.6139
DEFAULT_LON = 77.2090


def _validate(lat: float, lon: float):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(status_code=400, detail="lat must be -90..90, lon -180..180")


def _prov(source: str) -> Provenance:
    return Provenance(
        source=source,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        is_mock=True,
        is_live=False,
        data_mode="mock",
        scenario_id=engine.get_scenario_id(),
        tick=engine.get_tick(),
        freshness_sec=0.0,
    )


@router.get("/observations")
def get_observations(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    region_name: str = Query("Delhi-NCR"),
):
    _validate(lat, lon)
    state = fusion.fuse(lat, lon, region_name)
    return {
        "location": state.location,
        "scenario_id": state.scenario_id,
        "tick": state.tick,
        "timestamp_utc": state.timestamp_utc,
        "radar": state.radar,
        "satellite": state.satellite,
        "lightning": state.lightning,
        "model": state.model,
        "missing_sources": state.missing_sources,
        "is_mock": True,
    }


@router.get("/state")
def get_state(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    region_name: str = Query("Delhi-NCR"),
):
    _validate(lat, lon)
    return fusion.fuse(lat, lon, region_name)


@router.get("/cells")
def get_cells():
    raw = engine.gen_cells()
    cells = [
        StormCell(
            cell_id=c["cell_id"],
            center_lat=c["center_lat"],
            center_lon=c["center_lon"],
            intensity=c["intensity"],  # type: ignore
            max_reflectivity_dbz=c["max_reflectivity_dbz"],
            speed_kmh=c["speed_kmh"],
            direction_deg=c["direction_deg"],
            flash_rate_per_min=c["flash_rate_per_min"],
            lightning_jump=c["lightning_jump"],
            radius_km=c["radius_km"],
            provenance=_prov("tracker"),
        )
        for c in raw
    ]
    return {"cells": cells, "count": len(cells), "scenario_id": engine.get_scenario_id(), "tick": engine.get_tick(), "is_mock": True}


@router.get("/prediction")
def get_prediction(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
    horizon_min: int = Query(30, ge=0, le=120),
):
    _validate(lat, lon)
    state = fusion.fuse(lat, lon)
    # Phase 1: persistence heuristic — decay prob slightly with lead time (transparent)
    decay = max(0.55, 1.0 - horizon_min * 0.004)
    sp = round(state.storm_prob_pct * decay, 1)
    lp = round(state.lightning_prob_pct * decay, 1)
    return Prediction(
        location=state.location,
        horizon_min=horizon_min,
        storm_prob_pct=sp,
        lightning_prob_pct=lp,
        risk_level=risk_from_prob(sp),
        confidence_pct=round(max(35, state.confidence_pct - horizon_min * 0.15), 1),
        provenance=_prov("nowcast-heuristic-v0"),
    )


SAFETY = {
    "low": "No action needed. Stay weather-aware.",
    "moderate": "Thunderstorm possible. Avoid open fields; secure loose objects.",
    "high": "Thunderstorm likely. Move indoors; unplug sensitive electronics; avoid travel.",
    "severe": "Severe storm + frequent lightning likely. Stay indoors away from windows; do not shelter under trees.",
}


@router.get("/alerts")
def get_alerts(
    lat: float = Query(DEFAULT_LAT),
    lon: float = Query(DEFAULT_LON),
):
    _validate(lat, lon)
    state = fusion.fuse(lat, lon)
    alerts: list[Alert] = []
    if state.risk_level in ("high", "severe"):
        alerts.append(
            Alert(
                alert_id=f"AL-{engine.get_scenario_id()[:3].upper()}-T{engine.get_tick():03d}",
                location=state.location,
                location_name=state.location.region_name,
                risk_level=state.risk_level,
                storm_prob_pct=state.storm_prob_pct,
                confidence_pct=state.confidence_pct,
                message=f"{state.risk_level.upper()} thunderstorm risk ({state.storm_prob_pct}% storm, {state.lightning_prob_pct}% lightning). {SAFETY[state.risk_level]} [SIMULATED DEMO — not an official IMD warning]",
                status="active",
                provenance=_prov("alerts"),
            )
        )
    return {"alerts": alerts, "count": len(alerts), "is_mock": True, "note": "SIMULATED DEMO alerts — not official IMD warnings"}
