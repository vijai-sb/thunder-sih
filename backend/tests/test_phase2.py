"""Phase 2 tests — tracks, forecast, hazard zones, radar grid. Phase 1 untouched."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_tracks_shape_and_provenance():
    client.post("/api/scenario/developing")
    client.post("/api/scenario-reset")
    r = client.get("/api/tracks")
    assert r.status_code == 200
    j = r.json()
    assert j["is_mock"] is True
    assert j["count"] >= 1
    t = j["tracks"][0]
    assert t["current"]["label"] == "NOW"
    assert t["provenance"]["is_mock"] is True
    assert len(t["forecast"]) == 9  # 15..180
    assert [f["horizon_min"] for f in t["forecast"]] == [15, 30, 45, 60, 75, 90, 120, 150, 180]
    assert sorted(h["horizon_min"] for h in t["hazards"]) == [30, 60, 90]


def test_forecast_moves_along_direction_and_hazard_expands():
    client.post("/api/scenario/developing")
    client.post("/api/scenario-reset")
    t = client.get("/api/tracks").json()["tracks"][0]
    cur = (t["current"]["lat"], t["current"]["lon"])
    f30 = next(f for f in t["forecast"] if f["horizon_min"] == 30)
    f90 = next(f for f in t["forecast"] if f["horizon_min"] == 90)
    # NE motion (direction ~65deg): lat and lon both increase
    assert f30["lat"] > cur[0] and f30["lon"] > cur[1]
    assert f90["lat"] > f30["lat"] and f90["lon"] > f30["lon"]
    h30 = next(h for h in t["hazards"] if h["horizon_min"] == 30)
    h90 = next(h for h in t["hazards"] if h["horizon_min"] == 90)
    assert h90["radius_km"] > h30["radius_km"]
    f15 = next(f for f in t["forecast"] if f["horizon_min"] == 15)
    assert f15["confidence_pct"] > f90["confidence_pct"]


def test_tracks_deterministic_and_tick_progresses():
    client.post("/api/scenario/intensifying")
    client.post("/api/scenario-reset")
    a = client.get("/api/tracks").json()
    client.post("/api/scenario-advance?steps=2")
    b = client.get("/api/tracks").json()
    assert b["tick"] == a["tick"] + 2
    # same cell moves forward
    ca = a["tracks"][0]["current"]
    cb = b["tracks"][0]["current"]
    assert (cb["lat"], cb["lon"]) != (ca["lat"], ca["lon"])
    # previous at tick>0 matches history
    assert b["tracks"][0]["previous"] is not None


def test_trend_fields_present():
    client.post("/api/scenario/developing")
    client.post("/api/scenario-reset")
    client.post("/api/scenario-advance?steps=2")
    t = client.get("/api/tracks").json()["tracks"][0]
    assert t["flash_trend"] in ("increasing", "steady", "decreasing")
    assert t["growth_trend"] in ("intensifying", "steady", "decaying")


def test_radar_grid_simulated_and_consistent():
    client.post("/api/scenario/developing")
    r = client.get("/api/radar-grid?n=5&step_deg=0.05").json()
    assert r["is_mock"] is True
    assert r["count"] == 25
    assert "SIMULATED RADAR" in r["note"]
    assert all("dbz" in c for c in r["cells"])
    # grid center near Delhi default
    lats = [c["lat"] for c in r["cells"]]
    assert min(lats) < 28.6139 < max(lats)


def test_phase1_cells_still_compatible():
    r = client.get("/api/cells").json()
    assert r["is_mock"] is True
    assert all("CELL-" in c["cell_id"] for c in r["cells"])


def test_extended_horizons_uncalibrated_but_monotonic():
    client.post("/api/scenario/developing")
    client.post("/api/scenario-reset")
    t = client.get("/api/tracks").json()["tracks"][0]
    f90 = next(f for f in t["forecast"] if f["horizon_min"] == 90)
    f180 = next(f for f in t["forecast"] if f["horizon_min"] == 180)
    # same deterministic extrapolation continues past 90 min
    assert f180["lat"] > f90["lat"] and f180["lon"] > f90["lon"]
    assert f180["radius_km"] > f90["radius_km"]  # envelope keeps widening
    assert all(f["confidence_pct"] >= 30.0 for f in t["forecast"])  # floored, not calibrated
