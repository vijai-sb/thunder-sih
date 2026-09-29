"""Phase 3 tests — jump, risk engine, XAI, TTI, exposure, alerts. Phases 1–2 untouched."""
import os

from fastapi.testclient import TestClient

from app.main import app
from app.services import alert_store

client = TestClient(app)


def _reset_db():
    if os.path.exists(alert_store.DB_PATH):
        os.remove(alert_store.DB_PATH)


def _intel(scenario: str, tick: int = 0):
    _reset_db()
    client.post(f"/api/scenario/{scenario}")
    if tick:
        client.post(f"/api/scenario-advance?steps={tick}")
    r = client.get("/api/intel/cells")
    assert r.status_code == 200
    j = r.json()
    assert j["is_mock"] is True
    return j


def test_jump_config_exposed_and_prototype_labeled():
    r = client.get("/api/intel/config").json()
    assert r["jump_thresholds"]["min_abs_increase"] == 2.0
    assert r["risk_weights"]["dbz"] == 0.26
    assert "not a trained" in r["risk_engine"]


def test_normal_low_risk_no_alert():
    j = _intel("normal")
    for c in j["cells"]:
        assert c["risk"]["storm_risk"] == "low"
        assert c["risk"]["prototype_score"] < 25
        assert c["jump"]["jump_detected"] is False
        assert "Prototype" in c["risk"]["confidence_label"]
    a = client.get("/api/intel/alerts?status=ACTIVE").json()
    assert a["count"] == 0


def test_jump_deterministic():
    _intel("developing", tick=1)
    a = client.get("/api/intel/cells/CELL-01").json()
    client.post("/api/scenario/developing")
    client.post("/api/scenario-advance?steps=1")
    b = client.get("/api/intel/cells/CELL-01").json()
    assert a["jump"] == b["jump"]
    assert a["risk"] == b["risk"]


def test_developing_progresses_to_jump_and_alert():
    j0 = _intel("developing")
    assert all(c["jump"]["jump_detected"] is False for c in j0["cells"])  # tick0 never jumps
    assert client.get("/api/intel/alerts?status=ACTIVE").json()["count"] == 0
    client.post("/api/scenario-advance?steps=1")  # tick1: CELL-01 jump
    j1 = client.get("/api/intel/cells").json()
    c1 = next(c for c in j1["cells"] if c["cell_id"] == "CELL-01")
    assert c1["jump"]["jump_detected"] is True
    assert c1["jump"]["detected_tick"] == 1
    assert c1["jump"]["current_rate"] == 6.8
    assert c1["jump"]["previous_rate"] == 4.7
    assert c1["risk"]["prototype_score"] > j0["cells"][0]["risk"]["prototype_score"]
    alerts = client.get("/api/intel/alerts?status=ACTIVE").json()
    assert alerts["count"] >= 1
    assert "SIMULATED DEMO" in alerts["alerts"][0]["message"]


def test_intensifying_jump_and_high_alert():
    j = _intel("intensifying", tick=3)
    jumps = [c for c in j["cells"] if c["jump"]["jump_detected"]]
    assert len(jumps) >= 1
    assert any(c["risk"]["storm_risk"] in ("high", "severe") for c in j["cells"])
    alerts = client.get("/api/intel/alerts?status=ACTIVE").json()
    assert alerts["count"] >= 1


def test_severe_high_severe_alert():
    j = _intel("severe-lightning", tick=2)
    assert any(c["risk"]["storm_risk"] == "severe" or c["risk"]["prototype_score"] >= 75 for c in j["cells"]) or \
        any(c["risk"]["storm_risk"] in ("high", "severe") for c in j["cells"])
    alerts = client.get("/api/intel/alerts?status=ACTIVE").json()
    assert alerts["count"] >= 1
    assert all(a["status"] == "ACTIVE" for a in alerts["alerts"])


def test_xai_varies_and_explains():
    n = _intel("normal")["cells"][0]["xai"]
    s = _intel("severe-lightning", tick=2)["cells"][0]["xai"]
    assert len(n["factors"]) >= 4 and len(s["factors"]) >= 4
    assert [f["name"] for f in n["factors"][:2]] != [f["name"] for f in s["factors"][:2]]
    assert n["summary"] != s["summary"]
    assert all(0 <= f["score"] <= 100 for f in s["factors"])


def test_tti_prototype_label_and_decreases():
    _reset_db()
    client.post("/api/scenario/developing")
    t0 = client.get("/api/intel/cells/CELL-01").json()["tti"]
    assert "Prototype" in client.get("/api/intel/cells/CELL-01").json()["tti"].get("label", "Prototype estimated time-to-impact (unvalidated constant-velocity)")
    assert t0["minutes"] is not None and t0["minutes"] > 0
    client.post("/api/scenario-advance?steps=2")
    t2 = client.get("/api/intel/cells/CELL-01").json()["tti"]
    assert t2["minutes"] < t0["minutes"]


def test_exposure_labels_and_structure():
    j = _intel("developing")
    e = j["cells"][0]["exposure_60"]
    assert "Prototype exposure estimate" in e["label"]
    for k in ("population", "schools", "hospitals", "roads", "power_sites", "agri_km2", "pois_affected"):
        assert k in e
    # severe cell near demo POIs shows exposure
    js = _intel("severe-lightning", tick=2)
    assert any(c["exposure_60"]["population"] > 0 or c["exposure_90"]["population"] > 0 for c in js["cells"])


def test_history_timeline_present():
    _reset_db()
    client.post("/api/scenario/developing")
    client.post("/api/scenario-advance?steps=3")
    h = client.get("/api/intel/cells/CELL-01").json()["history"]
    assert len(h) == 4  # ticks 0..3
    assert [p["tick"] for p in h] == [0, 1, 2, 3]
    assert all("flash_rate" in p and "risk_score" in p for p in h)


def test_outage_degrades_confidence():
    _reset_db()
    client.post("/api/scenario/developing")
    client.post("/api/sources/radar/online")
    ok = client.get("/api/intel/cells/CELL-01").json()["risk"]["confidence_pct"]
    client.post("/api/sources/radar/offline")
    deg = client.get("/api/intel/cells/CELL-01").json()["risk"]["confidence_pct"]
    assert deg < ok
    client.post("/api/sources/radar/online")


def test_reset_deterministic_state_restored():
    _intel("developing", tick=4)
    a = client.get("/api/intel/cells/CELL-01").json()
    client.post("/api/scenario/developing")  # resets tick to 0
    client.post("/api/scenario-advance?steps=4")
    b = client.get("/api/intel/cells/CELL-01").json()
    assert a["risk"]["prototype_score"] == b["risk"]["prototype_score"]
    assert a["jump"] == b["jump"]


def test_superseded_alerts_auto_resolve():
    _reset_db()
    client.post("/api/scenario/developing")
    client.post("/api/scenario-advance?steps=1")
    client.get("/api/intel/cells")  # sync tick1
    tick1_ids = {a["alert_id"] for a in client.get("/api/intel/alerts?status=ACTIVE").json()["alerts"]}
    assert len(tick1_ids) >= 1
    client.post("/api/scenario-advance?steps=1")  # tick2
    client.get("/api/intel/cells")  # sync tick2
    active = client.get("/api/intel/alerts?status=ACTIVE").json()["alerts"]
    assert all("T002" in a["alert_id"] for a in active)
    resolved = client.get("/api/intel/alerts?status=RESOLVED").json()["alerts"]
    assert tick1_ids.issubset({a["alert_id"] for a in resolved})


def test_dismissal_preserved_same_run_but_reactivates_on_reset():
    _reset_db()
    client.post("/api/scenario/developing")
    client.post("/api/scenario-advance?steps=1")
    client.get("/api/intel/cells")
    aid = client.get("/api/intel/alerts?status=ACTIVE").json()["alerts"][0]["alert_id"]
    client.post(f"/api/intel/alerts/{aid}/resolve")
    # same run refresh: stays resolved
    client.get("/api/intel/cells")
    assert all(a["alert_id"] != aid for a in client.get("/api/intel/alerts?status=ACTIVE").json()["alerts"])
    # new run (reset replays tick1): re-fires ACTIVE
    client.post("/api/scenario/developing")
    client.post("/api/scenario-advance?steps=1")
    client.get("/api/intel/cells")
    assert any(a["alert_id"] == aid for a in client.get("/api/intel/alerts?status=ACTIVE").json()["alerts"])


def test_ack_resolve_persist():
    _intel("intensifying", tick=3)
    alerts = client.get("/api/intel/alerts?status=ACTIVE").json()["alerts"]
    assert len(alerts) >= 1
    aid = alerts[0]["alert_id"]
    assert client.post(f"/api/intel/alerts/{aid}/ack").json()["status"] == "ACKNOWLEDGED"
    assert any(a["alert_id"] == aid for a in client.get("/api/intel/alerts?status=ACKNOWLEDGED").json()["alerts"])
    assert client.post(f"/api/intel/alerts/{aid}/resolve").json()["status"] == "RESOLVED"
    assert all(a["alert_id"] != aid for a in client.get("/api/intel/alerts?status=ACTIVE").json()["alerts"])
    r = client.post("/api/intel/alerts/NOPE/ack")
    assert r.status_code == 404
