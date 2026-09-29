"""Phase 4 tests — demo mode, POIs, escalation data, i18n parity. Earlier phases untouched."""
import json
import os

from fastapi.testclient import TestClient

from app.main import app
from app.services import alert_store

client = TestClient(app)
FRONTEND = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")


def _reset_db():
    if os.path.exists(alert_store.DB_PATH):
        os.remove(alert_store.DB_PATH)


def test_demo_plan_shape():
    j = client.get("/api/demo/plan").json()
    assert j["count"] == 7
    assert j["steps"][0] == {"stage": "T+00", "scenario_id": "developing", "tick": 0, "caption": "Developing storm — cells organizing"}
    assert j["steps"][3]["caption"].startswith("LIGHTNING JUMP")
    assert "not real forecast times" in j["note"]


def test_demo_goto_matches_manual():
    _reset_db()
    client.post("/api/demo/goto", json={"scenario_id": "developing", "tick": 1})
    via_goto = client.get("/api/intel/cells/CELL-01").json()
    client.post("/api/scenario/developing")
    client.post("/api/scenario-advance?steps=1")
    manual = client.get("/api/intel/cells/CELL-01").json()
    assert via_goto["jump"] == manual["jump"]
    assert via_goto["risk"]["prototype_score"] == manual["risk"]["prototype_score"]
    assert via_goto["jump"]["jump_detected"] is True


def test_demo_goto_validation():
    assert client.post("/api/demo/goto", json={"scenario_id": "nope", "tick": 0}).status_code == 400
    assert client.post("/api/demo/goto", json={"scenario_id": "developing", "tick": 99}).status_code == 400


def test_demo_full_arc_fires_alerts():
    _reset_db()
    plan = client.get("/api/demo/plan").json()["steps"]
    saw_jump = saw_high = saw_alert = False
    for s in plan:
        client.post("/api/demo/goto", json={"scenario_id": s["scenario_id"], "tick": s["tick"]})
        intel = client.get("/api/intel/cells").json()
        if any(c["jump"]["jump_detected"] for c in intel["cells"]):
            saw_jump = True
        if any(c["risk"]["storm_risk"] in ("high", "severe") for c in intel["cells"]):
            saw_high = True
        if client.get("/api/intel/alerts?status=ACTIVE").json()["count"] > 0:
            saw_alert = True
    assert saw_jump and saw_high and saw_alert


def test_pois_simulated_and_complete():
    j = client.get("/api/pois").json()
    assert j["is_mock"] is True
    assert j["count"] == 19
    assert "SIMULATED DEMO INFRASTRUCTURE" in j["note"]
    kinds = {p["kind"] for p in j["pois"]}
    assert {"population", "school", "hospital", "road", "power", "agri"} <= kinds
    assert all("(demo)" in p["name"] for p in j["pois"])


def test_escalation_payload_has_tti_and_trigger():
    _reset_db()
    client.post("/api/demo/goto", json={"scenario_id": "intensifying", "tick": 3})
    client.get("/api/intel/cells")
    alerts = client.get("/api/intel/alerts?status=ACTIVE").json()["alerts"]
    assert len(alerts) >= 1
    a = alerts[0]
    assert a["trigger"] and a["cell_id"] and a["severity"] in ("high", "severe")
    assert "SIMULATED DEMO" in a["message"]


def test_citizen_i18n_parity():
    path = os.path.join(FRONTEND, "src", "lib", "warnings.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert set(data.keys()) == {"en", "ta", "hi"}
    en_keys = set(data["en"].keys())
    assert len(en_keys) >= 10
    for lang in ("ta", "hi"):
        assert set(data[lang].keys()) == en_keys, f"key mismatch in {lang}"
        for k in en_keys:
            assert isinstance(data[lang][k], str) and data[lang][k].strip(), f"empty {lang}.{k}"
    # technical terms stay English-only by design (dashboard not translated)
    assert "CAPE" not in " ".join(data["ta"].values())
