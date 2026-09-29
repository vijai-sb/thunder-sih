"""Phase 3 impact/exposure — deterministic SIMULATED demo POIs + prototype TTI.

POIs are invented demo points around Delhi-NCR. NOT real sensitive
infrastructure data. Exposure = POIs inside predicted hazard circles.
TTI = along-track arrival via constant-velocity (unvalidated).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

POIS: List[Dict] = [
    {"poi_id": "POP-CP", "name": "Connaught Place (demo)", "kind": "population", "lat": 28.6315, "lon": 77.2167, "population": 45000},
    {"poi_id": "POP-KB", "name": "Karol Bagh (demo)", "kind": "population", "lat": 28.6519, "lon": 77.1907, "population": 38000},
    {"poi_id": "POP-LN", "name": "Lajpat Nagar (demo)", "kind": "population", "lat": 28.5677, "lon": 77.2433, "population": 30000},
    {"poi_id": "POP-RH", "name": "Rohini (demo)", "kind": "population", "lat": 28.7400, "lon": 77.1120, "population": 52000},
    {"poi_id": "POP-DW", "name": "Dwarka (demo)", "kind": "population", "lat": 28.5921, "lon": 77.0460, "population": 41000},
    {"poi_id": "SCH-DPS", "name": "DPS school (demo)", "kind": "school", "lat": 28.6130, "lon": 77.2300},
    {"poi_id": "SCH-SM", "name": "St Mary school (demo)", "kind": "school", "lat": 28.6600, "lon": 77.2000},
    {"poi_id": "SCH-RH", "name": "Rohini school (demo)", "kind": "school", "lat": 28.7450, "lon": 77.1150},
    {"poi_id": "HSP-AI", "name": "AIIMS hospital (demo)", "kind": "hospital", "lat": 28.5672, "lon": 77.2100},
    {"poi_id": "HSP-SJ", "name": "Safdarjung hospital (demo)", "kind": "hospital", "lat": 28.5670, "lon": 77.2080},
    {"poi_id": "RD-NH48", "name": "NH-48 corridor (demo)", "kind": "road", "lat": 28.6000, "lon": 77.1500},
    {"poi_id": "RD-RING", "name": "Ring Road (demo)", "kind": "road", "lat": 28.6500, "lon": 77.2500},
    {"poi_id": "RD-YAM", "name": "Yamuna crossing (demo)", "kind": "road", "lat": 28.6200, "lon": 77.2600},
    {"poi_id": "PWR-OK", "name": "Okhla substation (demo)", "kind": "power", "lat": 28.5350, "lon": 77.2700},
    {"poi_id": "PWR-RH", "name": "Rohini substation (demo)", "kind": "power", "lat": 28.7500, "lon": 77.1100},
    {"poi_id": "AGR-PL", "name": "Palla fields (demo)", "kind": "agri", "lat": 28.8000, "lon": 77.1500, "area_km2": 18.0},
    {"poi_id": "AGR-CH", "name": "Chhawla fields (demo)", "kind": "agri", "lat": 28.5600, "lon": 77.0500, "area_km2": 13.0},
    {"poi_id": "POP-GZ", "name": "Ghaziabad corridor (demo)", "kind": "population", "lat": 28.7200, "lon": 77.4000, "population": 35000},
    {"poi_id": "SCH-GZ", "name": "Ghaziabad school (demo)", "kind": "school", "lat": 28.7300, "lon": 77.4100},
]


def haversine_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    r = 6371.0
    dlat = math.radians(b_lat - a_lat)
    dlon = math.radians(b_lon - a_lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(a_lat)) * math.cos(math.radians(b_lat)) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _to_xy(lat0: float, dlat: float, dlon: float) -> tuple:
    return (dlat * 111.0, dlon * 111.0 * math.cos(math.radians(lat0)))


def time_to_impact(
    cell_lat: float, cell_lon: float, speed_kmh: float, direction_deg: float
) -> dict:
    """Nearest demo POI ahead of the motion vector (prototype, unvalidated)."""
    if speed_kmh < 1:
        return {"target_name": "", "minutes": None}
    rad = math.radians(direction_deg)
    ux, uy = math.sin(rad), math.cos(rad)  # east, north unit (approx)
    best: Optional[tuple] = None
    for p in POIS:
        dx, dy = _to_xy(cell_lat, p["lat"] - cell_lat, p["lon"] - cell_lon)
        along = dx * ux + dy * uy
        perp = abs(dx * uy - dy * ux)
        if along <= 0 or perp > 15.0:
            continue
        tti = along / speed_kmh * 60.0
        if best is None or tti < best[0]:
            best = (tti, p["name"])
    if best is None:
        return {"target_name": "", "minutes": None}
    return {"target_name": best[1], "minutes": round(best[0], 1)}


def exposure_forecast(forecast: List[dict]) -> Dict[int, dict]:
    """Exposure per hazard horizon from forecast centers+radii."""
    out: Dict[int, dict] = {}
    for f in forecast:
        h = f["horizon_min"] if isinstance(f, dict) else f.horizon_min
        clat = f["lat"] if isinstance(f, dict) else f.lat
        clon = f["lon"] if isinstance(f, dict) else f.lon
        rad = f["radius_km"] if isinstance(f, dict) else f.radius_km
        if h not in (30, 60, 90):
            continue
        hit = [p for p in POIS if haversine_km(clat, clon, p["lat"], p["lon"]) <= rad]
        kinds = [p["kind"] for p in hit]
        out[h] = {
            "horizon_min": h,
            "population": sum(p.get("population", 0) for p in hit),
            "schools": kinds.count("school"),
            "hospitals": kinds.count("hospital"),
            "roads": kinds.count("road"),
            "power_sites": kinds.count("power"),
            "agri_km2": round(sum(p.get("area_km2", 0.0) for p in hit), 1),
            "pois_affected": [p["poi_id"] for p in hit],
            "label": "Prototype exposure estimate (simulated demo POIs — not real infrastructure data)",
        }
    for h in (30, 60, 90):
        out.setdefault(h, {"horizon_min": h, "population": 0, "schools": 0, "hospitals": 0, "roads": 0, "power_sites": 0, "agri_km2": 0.0, "pois_affected": [],
                           "label": "Prototype exposure estimate (simulated demo POIs — not real infrastructure data)"})
    return out
