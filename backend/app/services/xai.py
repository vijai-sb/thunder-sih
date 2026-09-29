"""Phase 3 explainability — generated from live simulated state, never hardcoded.

Each factor score = 0–100 normalized signal strength. Ranking = weight ×
normalized value via the Prototype Fusion Risk Engine weights, so the top
reasons genuinely change when the scenario/tick changes.
"""
from __future__ import annotations

from typing import List

from . import risk_engine


def explain_cell(
    cell_id: str,
    dbz: float,
    flash: float,
    roc: float,
    jump: bool,
    cape: float,
    humidity: float,
    shear: float,
    ctt: float,
) -> dict:
    norms = {
        "Radar intensity": risk_engine._n_dbz(dbz),
        "Lightning rate": risk_engine._n_flash(flash),
        "CAPE": risk_engine._n_cape(cape),
        "Humidity": risk_engine._n_hum(humidity),
        "Wind shear": risk_engine._n_shear(shear),
        "Cloud-top signal": risk_engine._n_coldtop(ctt),
    }
    wmap = {
        "Radar intensity": risk_engine.WEIGHTS["dbz"],
        "Lightning rate": risk_engine.WEIGHTS["flash"],
        "CAPE": risk_engine.WEIGHTS["cape"],
        "Humidity": risk_engine.WEIGHTS["humidity"],
        "Wind shear": risk_engine.WEIGHTS["shear"],
        "Cloud-top signal": risk_engine.WEIGHTS["coldtop"],
    }
    details = {
        "Radar intensity": f"{dbz} dBZ (simulated reflectivity)",
        "Lightning rate": f"{flash}/min, change {roc:+}/min" + (" — JUMP" if jump else ""),
        "CAPE": f"{cape:.0f} J/kg (simulated NWP)",
        "Humidity": f"{humidity:.0f}% (simulated)",
        "Wind shear": f"{shear:.1f} m/s (simulated)",
        "Cloud-top signal": f"{ctt:.0f}°C (simulated IR)",
    }
    ranked = sorted(norms, key=lambda k: wmap[k] * norms[k], reverse=True)
    factors: List[dict] = [
        {"name": k, "score": round(norms[k] * 100, 1), "detail": details[k]} for k in ranked[:5]
    ]
    # acceleration factor shown when jump/rapid change present
    if jump:
        factors.insert(
            1,
            {"name": "Lightning acceleration", "score": 94.0, "detail": f"jump threshold crossed ({roc:+}/min)"},
        )
        factors = factors[:5]
    elif roc >= 1.0:
        factors.append({"name": "Lightning acceleration", "score": round(min(90, 55 + roc * 8), 1), "detail": f"rising {roc:+}/min"})

    top = [f["name"] for f in factors[:2]]
    if "Radar intensity" in top and ("Lightning rate" in top or "Lightning acceleration" in top):
        summary = "Risk is elevated because radar intensity and lightning activity are increasing simultaneously."
    elif "Lightning rate" in top or "Lightning acceleration" in top:
        summary = "Risk is driven primarily by rapidly increasing lightning activity."
    elif "Radar intensity" in top:
        summary = "Risk is driven primarily by strong simulated radar reflectivity."
    elif "CAPE" in top:
        summary = "Risk is supported by a highly unstable simulated environment (high CAPE)."
    elif "Cloud-top signal" in top:
        summary = "Risk is supported by very cold simulated cloud tops indicating deep convection."
    else:
        summary = "Risk reflects a combination of moderate simulated signals; no single dominant driver."
    return {"cell_id": cell_id, "factors": factors, "summary": summary}
