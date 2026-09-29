"""Deterministic seeded simulation engine - Phase 1.

Same (scenario_id, tick, lat, lon) => same values.
Timestamp is fresh (now), values are reproducible.
All output is SIMULATED demo data.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from typing import Dict, List

DEFAULT_LAT = 28.6139  # Delhi
DEFAULT_LON = 77.2090
DEFAULT_REGION = "Delhi-NCR"

TICK_MINUTES = 5  # each Simulate Event advances 5 min sim time

SCENARIOS: Dict[str, dict] = {
    "normal": {
        "display_name": "Normal",
        "description": "Fair weather, no organized convection. Low CAPE, warm cloud tops.",
        "base_dbz": 20.0,
        "dbz_spread": 6.0,
        "growth_per_tick": 0.2,
        "base_flash": 0.2,
        "flash_spread": 0.8,
        "flash_growth": 0.05,
        "base_cape": 350.0,
        "base_shear": 4.0,
        "cloud_top": -18.0,
        "cells": [
            {"suffix": "01", "dlat": 0.06, "dlon": 0.05, "intensity": "weak", "speed": 12.0, "direction": 60.0},
        ],
    },
    "developing": {
        "display_name": "Developing Thunderstorm",
        "description": "Isolated cells organizing. Rising echo tops, cooling cloud tops, sporadic lightning.",
        "base_dbz": 38.0,
        "dbz_spread": 7.0,
        "growth_per_tick": 1.1,
        "base_flash": 4.0,
        "flash_spread": 3.0,
        "flash_growth": 0.9,
        "base_cape": 1250.0,
        "base_shear": 9.0,
        "cloud_top": -46.0,
        "cells": [
            {"suffix": "01", "dlat": 0.05, "dlon": 0.08, "intensity": "moderate", "speed": 24.0, "direction": 65.0},
            {"suffix": "02", "dlat": -0.07, "dlon": 0.12, "intensity": "moderate", "speed": 21.0, "direction": 70.0},
        ],
    },
    "intensifying": {
        "display_name": "Intensifying Thunderstorm",
        "description": "Maturing multicell. High reflectivity, cold overshooting tops, frequent lightning.",
        "base_dbz": 50.0,
        "dbz_spread": 7.0,
        "growth_per_tick": 1.4,
        "base_flash": 12.0,
        "flash_spread": 5.0,
        "flash_growth": 1.6,
        "base_cape": 2300.0,
        "base_shear": 14.0,
        "cloud_top": -62.0,
        "cells": [
            {"suffix": "01", "dlat": 0.05, "dlon": 0.08, "intensity": "strong", "speed": 32.0, "direction": 65.0},
            {"suffix": "02", "dlat": -0.07, "dlon": 0.12, "intensity": "strong", "speed": 29.0, "direction": 70.0},
            {"suffix": "03", "dlat": 0.12, "dlon": -0.06, "intensity": "moderate", "speed": 26.0, "direction": 60.0},
        ],
    },
    "severe-lightning": {
        "display_name": "Severe Lightning Event",
        "description": "Severe squall line. Very high flash rate with lightning jump signature.",
        "base_dbz": 57.0,
        "dbz_spread": 8.0,
        "growth_per_tick": 1.0,
        "base_flash": 26.0,
        "flash_spread": 9.0,
        "flash_growth": 2.2,
        "base_cape": 3200.0,
        "base_shear": 19.0,
        "cloud_top": -74.0,
        "cells": [
            {"suffix": "01", "dlat": 0.05, "dlon": 0.08, "intensity": "severe", "speed": 44.0, "direction": 65.0},
            {"suffix": "02", "dlat": -0.07, "dlon": 0.12, "intensity": "severe", "speed": 41.0, "direction": 70.0},
            {"suffix": "03", "dlat": 0.12, "dlon": -0.06, "intensity": "strong", "speed": 36.0, "direction": 60.0},
            {"suffix": "04", "dlat": -0.12, "dlon": -0.10, "intensity": "strong", "speed": 33.0, "direction": 75.0},
        ],
    },
}

_state = {"scenario_id": "developing", "tick": 0, "run_id": 1}
_forced_offline: set = set()


def get_run_id() -> int:
    return _state["run_id"]


def seeded_unit(*parts: object) -> float:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:12]
    return int(h, 16) / 16**12


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def get_scenario_id() -> str:
    return _state["scenario_id"]


def get_tick() -> int:
    return _state["tick"]


def set_scenario(scenario_id: str) -> dict:
    if scenario_id not in SCENARIOS:
        raise ValueError(f"unknown scenario '{scenario_id}'")
    _state["scenario_id"] = scenario_id
    _state["tick"] = 0
    _state["run_id"] += 1  # new demo run: prior dismissals must not suppress re-fire
    return current_info()


def advance_tick(steps: int = 1) -> dict:
    _state["tick"] = max(0, _state["tick"] + steps)
    return current_info()


def reset_clock() -> dict:
    _state["tick"] = 0
    _state["run_id"] += 1  # replay allowed to re-fire alerts
    return current_info()


def current_info() -> dict:
    return {
        "scenario_id": _state["scenario_id"],
        "tick": _state["tick"],
        "sim_time_utc": datetime.now(timezone.utc).isoformat(),
        "is_mock": True,
    }


def scenario_def(scenario_id: str | None = None) -> dict:
    sid = scenario_id or _state["scenario_id"]
    return SCENARIOS[sid]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def gen_radar(lat: float, lon: float) -> dict:
    sc = scenario_def()
    sid = get_scenario_id()
    tick = get_tick()
    rlat, rlon = round(lat, 2), round(lon, 2)
    s = seeded_unit(sid, tick, rlat, rlon, "radar")
    dbz = sc["base_dbz"] + s * sc["dbz_spread"] + tick * sc["growth_per_tick"]
    dbz = clamp(dbz, 5, 72)
    return {
        "reflectivity_dbz": round(dbz, 1),
        "velocity_ms": round((seeded_unit(sid, tick, rlat, rlon, "vel") - 0.5) * 24, 1),
        "echo_top_km": round(clamp(3.5 + dbz * 0.16 + s * 1.5, 2, 18), 1),
        "vil_kgm2": round(clamp(dbz * 0.55 + s * 4, 0, 45), 1),
    }


def gen_satellite(lat: float, lon: float) -> dict:
    sc = scenario_def()
    sid = get_scenario_id()
    tick = get_tick()
    rlat, rlon = round(lat, 2), round(lon, 2)
    s = seeded_unit(sid, tick, rlat, rlon, "sat")
    ctt = sc["cloud_top"] - tick * 0.9 - s * 6.0
    ctt = clamp(ctt, -85, 5)
    cth = clamp(5.0 + (10 - ctt) * 0.09 + s, 2, 17)
    if ctt < -60:
        ctype = "cumulonimbus (overshooting top)"
    elif ctt < -40:
        ctype = "cumulonimbus"
    elif ctt < -25:
        ctype = "cumulus congestus"
    else:
        ctype = "fair-weather cumulus"
    return {
        "cloud_top_temp_c": round(ctt, 1),
        "cloud_top_height_km": round(cth, 1),
        "cloud_type": ctype,
        "ir_brightness": round(clamp(300 + ctt * 1.4, 180, 300), 1),
        "wv_brightness": round(clamp(280 + ctt * 0.9, 190, 290), 1),
    }


def gen_lightning(lat: float, lon: float) -> dict:
    sc = scenario_def()
    sid = get_scenario_id()
    tick = get_tick()
    rlat, rlon = round(lat, 2), round(lon, 2)
    s = seeded_unit(sid, tick, rlat, rlon, "ltg")
    flash = sc["base_flash"] + s * sc["flash_spread"] + tick * sc["flash_growth"]
    flash = clamp(flash, 0, 55)
    count5 = int(round(flash * 5))
    avg_ka = round(12 + seeded_unit(sid, tick, rlat, rlon, "ka") * 38, 1)
    strikes = []
    n = min(count5, 20)
    for i in range(n):
        js = seeded_unit(sid, tick, rlat, rlon, f"strike-{i}")
        js2 = seeded_unit(sid, tick, rlat, rlon, f"strike-y-{i}")
        slat = lat + (js - 0.5) * 0.22
        slon = lon + (js2 - 0.5) * 0.22
        strikes.append(
            {
                "strike_id": f"{sid[:3].upper()}-T{tick:03d}-{i+1:02d}",
                "lat": round(slat, 4),
                "lon": round(slon, 4),
                "timestamp_utc": utcnow_iso(),
                "peak_current_ka": round(5 + seeded_unit(sid, tick, i, "amp") * 75, 1),
                "polarity": "-" if seeded_unit(sid, tick, i, "pol") < 0.85 else "+",
            }
        )
    return {
        "strike_count_5min": count5,
        "flash_rate_per_min": round(flash, 1),
        "avg_peak_current_ka": avg_ka,
        "strikes": strikes,
    }


def gen_model(lat: float, lon: float) -> dict:
    sc = scenario_def()
    sid = get_scenario_id()
    tick = get_tick()
    rlat, rlon = round(lat, 2), round(lon, 2)
    s = seeded_unit(sid, tick, rlat, rlon, "nwp")
    s2 = seeded_unit(sid, tick, rlat, rlon, "nwp2")
    cape = clamp(sc["base_cape"] + s * 350 + tick * 60, 0, 4200)
    shear = clamp(sc["base_shear"] + s2 * 3 + tick * 0.3, 0, 30)
    return {
        "temp_c": round(33 - tick * 0.25 - s * 3.5, 1),
        "humidity_pct": round(clamp(58 + tick * 1.4 + s * 12, 20, 100), 1),
        "pressure_hpa": round(1006 - tick * 0.4 - s * 3, 1),
        "wind_speed_ms": round(clamp(3 + shear * 0.45 + s * 2, 0, 32), 1),
        "wind_dir_deg": round((240 + s2 * 50 + tick * 1.5) % 360, 1),
        "cape_jkg": round(cape, 1),
        "cin_jkg": round(clamp(-(30 + s * 90), -250, 0), 1),
        "shear_ms": round(shear, 1),
        "precip_mm": round(clamp((cape / 900) * (0.4 + s) + tick * 0.35, 0, 60), 1),
    }


def _cell_center(c: dict, tick: int) -> tuple:
    """Deterministic constant-velocity center for template c at tick."""
    rad = math.radians(c["direction"])
    dist_km = c["speed"] * tick * (TICK_MINUTES / 60.0)
    dlat = c["dlat"] + (dist_km * math.cos(rad)) / 111.0
    dlon = c["dlon"] + (dist_km * math.sin(rad)) / (111.0 * math.cos(math.radians(DEFAULT_LAT)))
    return (DEFAULT_LAT + dlat, DEFAULT_LON + dlon)


def _cell_values_at(clat: float, clon: float, tick: int) -> tuple:
    """Deterministic radar/flash values at a position for an arbitrary tick.

    Uses the same seeded formulas as gen_radar/gen_lightning but with an
    explicit tick so tracking can query history (tick-1) without mutating state.
    """
    sc = scenario_def()
    sid = get_scenario_id()
    rlat, rlon = round(clat, 2), round(clon, 2)
    s = seeded_unit(sid, tick, rlat, rlon, "radar")
    dbz = clamp(sc["base_dbz"] + s * sc["dbz_spread"] + tick * sc["growth_per_tick"], 5, 72)
    s2 = seeded_unit(sid, tick, rlat, rlon, "ltg")
    flash = clamp(sc["base_flash"] + s2 * sc["flash_spread"] + tick * sc["flash_growth"], 0, 55)
    return (round(dbz, 1), round(flash, 1))


def gen_cells_at(tick: int) -> List[dict]:
    """Cells at an arbitrary tick (pure — does not mutate global clock)."""
    sc = scenario_def()
    sid = get_scenario_id()
    out = []
    for c in sc["cells"]:
        clat, clon = _cell_center(c, tick)
        dbz, flash = _cell_values_at(clat, clon, tick)
        jump = flash > (sc["base_flash"] + 8) and sid in ("intensifying", "severe-lightning")
        out.append(
            {
                "cell_id": f"CELL-{c['suffix']}",
                "center_lat": round(clat, 4),
                "center_lon": round(clon, 4),
                "intensity": c["intensity"],
                "max_reflectivity_dbz": dbz,
                "speed_kmh": c["speed"],
                "direction_deg": c["direction"],
                "flash_rate_per_min": flash,
                "lightning_jump": jump,
                "radius_km": 8.0 if c["intensity"] in ("weak", "moderate") else 12.0,
            }
        )
    return out


def gen_cells() -> List[dict]:
    return gen_cells_at(get_tick())


def gen_radar_grid(n: int = 7, step_deg: float = 0.05) -> List[dict]:
    """Deterministic simulated reflectivity grid around default center.

    Prototype heat representation — NOT a real IMD raster. Values come from
    the same seeded gen_radar() so grid and point obs stay consistent.
    """
    sid = get_scenario_id()
    tick = get_tick()
    half = n // 2
    grid = []
    for i in range(n):
        for j in range(n):
            glat = round(DEFAULT_LAT + (i - half) * step_deg, 4)
            glon = round(DEFAULT_LON + (j - half) * step_deg, 4)
            r = gen_radar(glat, glon)
            grid.append({"lat": glat, "lon": glon, "dbz": r["reflectivity_dbz"]})
    return grid


def model_at(lat: float, lon: float, tick: int) -> dict:
    """Pure NWP values at an explicit tick (no clock mutation; for history/risk)."""
    sc = scenario_def()
    sid = get_scenario_id()
    rlat, rlon = round(lat, 2), round(lon, 2)
    s = seeded_unit(sid, tick, rlat, rlon, "nwp")
    s2 = seeded_unit(sid, tick, rlat, rlon, "nwp2")
    cape = clamp(sc["base_cape"] + s * 350 + tick * 60, 0, 4200)
    shear = clamp(sc["base_shear"] + s2 * 3 + tick * 0.3, 0, 30)
    return {
        "cape_jkg": round(cape, 1),
        "shear_ms": round(shear, 1),
        "humidity_pct": round(clamp(58 + tick * 1.4 + s * 12, 20, 100), 1),
    }


def satellite_at(lat: float, lon: float, tick: int) -> dict:
    """Pure satellite values at an explicit tick (no clock mutation)."""
    sc = scenario_def()
    sid = get_scenario_id()
    rlat, rlon = round(lat, 2), round(lon, 2)
    s = seeded_unit(sid, tick, rlat, rlon, "sat")
    ctt = clamp(sc["cloud_top"] - tick * 0.9 - s * 6.0, -85, 5)
    return {"cloud_top_temp_c": round(ctt, 1)}


def set_source_offline(source_id: str, offline: bool = True) -> None:
    if offline:
        _forced_offline.add(source_id)
    else:
        _forced_offline.discard(source_id)


def is_offline(source_id: str) -> bool:
    return source_id in _forced_offline


def offline_sources() -> List[str]:
    return sorted(_forced_offline)


def list_scenarios() -> List[dict]:
    return [
        {"scenario_id": sid, "display_name": v["display_name"], "description": v["description"]}
        for sid, v in SCENARIOS.items()
    ]
