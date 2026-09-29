"""Phase 2 tracking — lightweight deterministic Kalman-lite.

No ML, no scipy. Constant-velocity extrapolation from the seeded sim:
  previous = cells at tick-1 (pure query, no clock mutation)
  velocity = template speed/dir (km/h, degrees)
  forecast(h) = current + v * h  (hours)
  hazard radius grows with horizon to show uncertainty (NOT calibrated).

Trends compare tick vs tick-1 values (growth/decay).
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List

from ..models.schemas import (
    CellTrack,
    ForecastPoint,
    HazardZone,
    Provenance,
    TrackPoint,
)
from ..sim import engine

FORECAST_HORIZONS = [15, 30, 45, 60, 75, 90, 120, 150, 180]
HAZARD_HORIZONS = [30, 60, 90]

CARDINALS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def cardinal(deg: float) -> str:
    idx = int(((deg + 22.5) % 360) // 45)
    return CARDINALS[idx]


def _prov() -> Provenance:
    return Provenance(
        source="tracker",
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        is_mock=True,
        is_live=False,
        data_mode="mock",
        scenario_id=engine.get_scenario_id(),
        tick=engine.get_tick(),
        freshness_sec=0.0,
        note="SIMULATED DEMO tracking — constant-velocity extrapolation, not validated",
    )


def _dest(lat: float, lon: float, speed_kmh: float, direction_deg: float, minutes: int) -> tuple:
    """Destination from constant-velocity motion (equirectangular approx)."""
    dist_km = speed_kmh * (minutes / 60.0)
    rad = math.radians(direction_deg)
    dlat = (dist_km * math.cos(rad)) / 111.0
    dlon = (dist_km * math.sin(rad)) / (111.0 * math.cos(math.radians(lat)))
    return (round(lat + dlat, 4), round(lon + dlon, 4))


def get_tracks() -> List[CellTrack]:
    tick = engine.get_tick()
    now_cells = engine.gen_cells_at(tick)
    prev_cells = engine.gen_cells_at(tick - 1) if tick > 0 else []
    prev_by_id = {c["cell_id"]: c for c in prev_cells}
    prov = _prov()
    out: List[CellTrack] = []

    for c in now_cells:
        prev = prev_by_id.get(c["cell_id"])
        # trends from deterministic history
        if prev is not None:
            d_flash = c["flash_rate_per_min"] - prev["flash_rate_per_min"]
            d_dbz = c["max_reflectivity_dbz"] - prev["max_reflectivity_dbz"]
        else:
            d_flash = 0.0
            d_dbz = 0.0

        flash_trend = "increasing" if d_flash > 0.7 else ("decreasing" if d_flash < -0.7 else "steady")
        dbz_trend = "increasing" if d_dbz > 1.0 else ("decreasing" if d_dbz < -1.0 else "steady")
        if flash_trend == "increasing" or dbz_trend == "increasing":
            growth = "intensifying"
        elif flash_trend == "decreasing" and dbz_trend == "decreasing":
            growth = "decaying"
        else:
            growth = "steady"

        forecast: List[ForecastPoint] = []
        for h in FORECAST_HORIZONS:
            flat, flon = _dest(c["center_lat"], c["center_lon"], c["speed_kmh"], c["direction_deg"], h)
            # uncertainty grows with lead time; confidence decays (transparent, uncalibrated)
            radius = round(c["radius_km"] + h * 0.12, 1)
            conf = round(max(30.0, 88.0 - h * 0.45), 1)
            forecast.append(ForecastPoint(horizon_min=h, lat=flat, lon=flon, radius_km=radius, confidence_pct=conf))

        hazards: List[HazardZone] = []
        for h in HAZARD_HORIZONS:
            f = next(p for p in forecast if p.horizon_min == h)
            hazards.append(
                HazardZone(
                    horizon_min=h,
                    center_lat=f.lat,
                    center_lon=f.lon,
                    radius_km=f.radius_km,
                )
            )

        out.append(
            CellTrack(
                cell_id=c["cell_id"],
                intensity=c["intensity"],  # type: ignore
                current=TrackPoint(lat=c["center_lat"], lon=c["center_lon"], tick=tick, label="NOW"),
                previous=TrackPoint(lat=prev["center_lat"], lon=prev["center_lon"], tick=tick - 1, label="PREV")
                if prev
                else None,
                speed_kmh=c["speed_kmh"],
                direction_deg=c["direction_deg"],
                direction_cardinal=cardinal(c["direction_deg"]),
                flash_rate_per_min=c["flash_rate_per_min"],
                flash_trend=flash_trend,
                dbz_trend=dbz_trend,
                growth_trend=growth,  # type: ignore
                lightning_jump=c["lightning_jump"],
                forecast=forecast,
                hazards=hazards,
                provenance=prov,
            )
        )
    return out
