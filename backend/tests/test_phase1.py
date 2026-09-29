"""Phase 1 smoke tests — determinism + provenance + fallback."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_mock():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["is_mock"] is True


def test_scenario_switch_changes_data():
    client.post("/api/scenario/normal")
    a = client.get("/api/state").json()
    client.post("/api/scenario/severe-lightning")
    b = client.get("/api/state").json()
    assert a["scenario_id"] != b["scenario_id"]
    assert b["storm_prob_pct"] > a["storm_prob_pct"]


def test_determinism_same_tick_same_values():
    client.post("/api/scenario/developing")
    client.post("/api/scenario-reset")
    x = client.get("/api/state?lat=28.61&lon=77.20").json()
    # reset does not change scenario, tick 0 again -> same fused probs
    client.post("/api/scenario-reset")
    y = client.get("/api/state?lat=28.61&lon=77.20").json()
    assert x["storm_prob_pct"] == y["storm_prob_pct"]
    assert x["provenance"]["is_mock"] is True


def test_advance_tick_progresses():
    client.post("/api/scenario/developing")
    client.post("/api/scenario-reset")
    before = client.get("/api/state").json()
    client.post("/api/scenario-advance?steps=3")
    after = client.get("/api/state").json()
    assert after["tick"] == before["tick"] + 3
    # developing storm should intensify with ticks (growth_per_tick > 0)
    assert after["storm_prob_pct"] >= before["storm_prob_pct"]


def test_cells_and_provenance():
    client.post("/api/scenario/intensifying")
    r = client.get("/api/cells").json()
    assert r["is_mock"] is True
    assert r["count"] >= 2
    assert all("CELL-" in c["cell_id"] for c in r["cells"])


def test_fallback_offline_degrades():
    client.post("/api/scenario/developing")
    client.post("/api/scenario-reset")
    client.post("/api/sources/radar/online")
    ok = client.get("/api/state").json()
    assert "radar" not in ok["missing_sources"]
    client.post("/api/sources/radar/offline")
    deg = client.get("/api/state").json()
    assert "radar" in deg["missing_sources"]
    assert deg["data_health"] in ("degraded", "offline")
    assert deg["radar"] is None
    client.post("/api/sources/radar/online")


def test_invalid_coords_rejected():
    r = client.get("/api/state?lat=999&lon=999")
    assert r.status_code == 400
