"""Simulated radar adapter (future: IMD DWR mosaic)."""
from __future__ import annotations

from datetime import datetime, timezone

from .base import BaseAdapter
from ..sim import engine


class MockRadarAdapter(BaseAdapter):
    source_id = "radar"
    display_name = "Doppler Weather Radar (simulated)"
    latency_sec = 4.2

    def is_available(self) -> bool:
        return not engine.is_offline("radar")

    def get_latest(self, lat: float, lon: float) -> dict:
        if not self.is_available():
            raise ConnectionError("radar adapter offline (simulated outage)")
        vals = engine.gen_radar(lat, lon)
        vals["_meta"] = {
            "last_update_utc": datetime.now(timezone.utc).isoformat(),
            "latency_sec": self.latency_sec,
        }
        return vals
