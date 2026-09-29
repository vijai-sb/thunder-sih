"""Simulated NWP/model adapter (future: NCUM/WRF/GFS)."""
from __future__ import annotations

from datetime import datetime, timezone

from .base import BaseAdapter
from ..sim import engine


class MockModelAdapter(BaseAdapter):
    source_id = "nwp"
    display_name = "NWP Model Analysis (simulated)"
    latency_sec = 300.0

    def is_available(self) -> bool:
        return not engine.is_offline("nwp")

    def get_latest(self, lat: float, lon: float) -> dict:
        if not self.is_available():
            raise ConnectionError("nwp adapter offline (simulated outage)")
        vals = engine.gen_model(lat, lon)
        vals["_meta"] = {
            "last_update_utc": datetime.now(timezone.utc).isoformat(),
            "latency_sec": self.latency_sec,
        }
        return vals
