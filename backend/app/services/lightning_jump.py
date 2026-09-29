"""Phase 3 lightning-jump detection — deterministic, configurable, no randomness.

Jump when per-tick increase crosses ALL of:
  abs increase >= MIN_ABS_INCREASE (flashes/min)
  relative increase >= MIN_REL_INCREASE (fraction of previous rate)
  current rate >= MIN_FLASH (flashes/min)

`elevated` = weaker watch level. Thresholds live in JUMP_CONFIG and are
exposed via /api/intel/config — never hardcoded at call sites.
"""
from __future__ import annotations

from typing import Dict, List

from ..sim import engine

JUMP_CONFIG: Dict[str, float] = {
    "min_abs_increase": 2.0,
    "min_rel_increase": 0.10,
    "min_flash": 6.0,
    "elevated_abs": 1.0,
    "elevated_rel": 0.15,
    "elevated_min_flash": 5.0,
}


def _flash_series(cell_id: str, tick: int) -> List[float]:
    """Flash history tick-2..tick for a cell (pure queries)."""
    by_id_then = {c["cell_id"]: c for c in engine.gen_cells_at(max(0, tick - 2))}
    by_id_prev = {c["cell_id"]: c for c in engine.gen_cells_at(max(0, tick - 1))}
    by_id_now = {c["cell_id"]: c for c in engine.gen_cells_at(tick)}
    vals = []
    for d in (by_id_then, by_id_prev, by_id_now):
        c = d.get(cell_id)
        vals.append(float(c["flash_rate_per_min"]) if c else 0.0)
    if tick == 0:
        return [vals[2], vals[2], vals[2]]
    if tick == 1:
        return [vals[1], vals[1], vals[2]]
    return vals


def analyze_cell(cell_id: str, tick: int | None = None, _find_detected: bool = True) -> dict:
    t = engine.get_tick() if tick is None else tick
    prev2, prev, cur = _flash_series(cell_id, t)
    roc = round(cur - prev, 2)
    accel = round((cur - prev) - (prev - prev2), 2)
    rel = (roc / prev) if prev > 0 else (1.0 if roc > 0 else 0.0)
    trend = "increasing" if roc >= 1.0 else ("decreasing" if roc <= -1.0 else "steady")

    cfg = JUMP_CONFIG
    jump = (
        t > 0
        and roc >= cfg["min_abs_increase"]
        and rel >= cfg["min_rel_increase"]
        and cur >= cfg["min_flash"]
    )
    elevated = (
        not jump
        and t > 0
        and roc >= cfg["elevated_abs"]
        and rel >= cfg["elevated_rel"]
        and cur >= cfg["elevated_min_flash"]
    )
    status = "jump" if jump else ("elevated" if elevated else "none")

    detected_tick = None
    if jump and _find_detected:
        # earliest tick <= t where jump holds (tick small so linear scan is fine)
        for tt in range(1, t + 1):
            r = analyze_cell(cell_id, tt, _find_detected=False)
            if r["jump_detected"]:
                detected_tick = tt
                break

    return {
        "cell_id": cell_id,
        "current_rate": round(cur, 1),
        "previous_rate": round(prev, 1),
        "rate_of_change": roc,
        "acceleration": accel,
        "trend": trend,
        "jump_detected": jump,
        "status": status,
        "detected_tick": detected_tick,
    }


def all_cells() -> List[dict]:
    return [analyze_cell(c["cell_id"]) for c in engine.gen_cells_at(engine.get_tick())]
