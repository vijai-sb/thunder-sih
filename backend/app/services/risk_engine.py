"""Phase 3 Prototype Fusion Risk Engine — deterministic heuristic, NOT ML.

Named deliberately: "Prototype Fusion Risk Engine (heuristic — not a trained
ML model)". Outputs a 0–100 *Prototype Risk Score* (never "probability").

Swap point for a trained model: implement `RiskEngineProtocol.score(...)`
(e.g. ONNX/sklearn backed) and return it from `get_risk_engine()`. Callers
use the protocol, so no other code changes.
"""
from __future__ import annotations

from typing import Dict, Protocol

from ..models.schemas import risk_from_prob
from ..sim import engine

WEIGHTS: Dict[str, float] = {
    "dbz": 0.26,
    "flash": 0.22,
    "jump": 0.14,
    "cape": 0.14,
    "humidity": 0.05,
    "shear": 0.09,
    "coldtop": 0.10,
}
ENGINE_NAME = "Prototype Fusion Risk Engine (heuristic — not a trained ML model)"


def _n_dbz(v: float) -> float:
    return max(0.0, min(1.0, (v - 15) / 55.0))


def _n_flash(v: float) -> float:
    return max(0.0, min(1.0, v / 40.0))


def _n_cape(v: float) -> float:
    return max(0.0, min(1.0, v / 3500.0))


def _n_hum(v: float) -> float:
    return max(0.0, min(1.0, (v - 30) / 70.0))


def _n_shear(v: float) -> float:
    return max(0.0, min(1.0, v / 25.0))


def _n_coldtop(v: float) -> float:
    return max(0.0, min(1.0, (5 - v) / 85.0))


class RiskEngineProtocol(Protocol):
    def score(self, signals: dict) -> float:
        """Return 0–100 Prototype Risk Score from normalized signals."""
        ...


class PrototypeFusionRiskEngine:
    """Heuristic engine. Future trained model plugs in here via the protocol."""

    weights = WEIGHTS

    def score(self, signals: dict) -> float:
        s = (
            self.weights["dbz"] * _n_dbz(signals.get("dbz", 0))
            + self.weights["flash"] * _n_flash(signals.get("flash", 0))
            + self.weights["jump"] * (1.0 if signals.get("jump") else (0.4 if signals.get("trend") == "increasing" else 0.0))
            + self.weights["cape"] * _n_cape(signals.get("cape", 0))
            + self.weights["humidity"] * _n_hum(signals.get("humidity", 60))
            + self.weights["shear"] * _n_shear(signals.get("shear", 0))
            + self.weights["coldtop"] * _n_coldtop(signals.get("ctt", 0))
        )
        return round(100 * max(0.0, min(1.0, s)), 1)


def get_risk_engine() -> RiskEngineProtocol:
    # SWAP POINT: return a trained-model engine implementing .score(signals)
    return PrototypeFusionRiskEngine()


def lightning_risk_score(flash: float, jump: bool, trend: str) -> float:
    v = 0.60 * _n_flash(flash) + 0.25 * (1.0 if jump else 0.0) + 0.15 * (1.0 if trend == "increasing" else (0.4 if trend == "steady" else 0.0))
    return round(100 * v, 1)


def assess_cell(
    cell_id: str,
    dbz: float,
    flash: float,
    jump: bool,
    trend: str,
    growth: str,
    n_missing: int = 0,
) -> dict:
    """Score one cell using env at the cell center (respects outages via n_missing)."""
    cell = next((c for c in engine.gen_cells_at(engine.get_tick()) if c["cell_id"] == cell_id), None)
    lat = cell["center_lat"] if cell else engine.DEFAULT_LAT
    lon = cell["center_lon"] if cell else engine.DEFAULT_LON
    tick = engine.get_tick()
    offline = set(engine.offline_sources())
    m = engine.model_at(lat, lon, tick) if "nwp" not in offline else {"cape_jkg": 800.0, "shear_ms": 6.0, "humidity_pct": 60.0}
    s = engine.satellite_at(lat, lon, tick) if "satellite" not in offline else {"cloud_top_temp_c": -30.0}

    signals = {
        "dbz": dbz,
        "flash": flash,
        "jump": jump,
        "trend": trend,
        "cape": m["cape_jkg"],
        "humidity": m["humidity_pct"],
        "shear": m["shear_ms"],
        "ctt": s["cloud_top_temp_c"],
    }
    score = get_risk_engine().score(signals)
    lscore = lightning_risk_score(flash, jump, trend)
    confidence = round(max(35.0, min(95.0, 88.0 - 12 * n_missing)), 1)
    return {
        "cell_id": cell_id,
        "prototype_score": score,
        "storm_risk": risk_from_prob(score),
        "lightning_risk": risk_from_prob(lscore),
        "lightning_score": lscore,
        "intensification": growth,
        "confidence_pct": confidence,
        "env": m,
        "ctt": s["cloud_top_temp_c"],
    }
