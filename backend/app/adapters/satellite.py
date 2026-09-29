"""Simulated satellite adapter (future: INSAT-3D/3DR IR/WV)."""
from __future__ import annotations

from datetime import datetime, timezone

from .base import BaseAdapter
from ..sim import engine


class MockSatelliteAdapter(BaseAdapter):
    source_id = "satellite"
    display_name = "INSAT Satellite IR/WV (simulated)"
    latency_sec = 90.0

    def is_available(self) -> bool:
        return not engine.is_offline("satellite")

    def get_latest(self, lat: float, lon: float) -> dict:
        if not self.is_available():
            raise ConnectionError("satellite adapter offline (simulated outage)")
        vals = engine.gen_satellite(lat, lon)
        vals["_meta"] = {
            "last_update_utc": datetime.now(timezone.utc).isoformat(),
            "latency_sec": self.latency_sec,
        }
        return vals
