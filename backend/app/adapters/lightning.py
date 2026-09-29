"""Simulated lightning adapter (future: IITM/IMD lightning location network)."""
from __future__ import annotations

from datetime import datetime, timezone

from .base import BaseAdapter
from ..sim import engine


class MockLightningAdapter(BaseAdapter):
    source_id = "lightning"
    display_name = "Lightning Location Network (simulated)"
    latency_sec = 2.0

    def is_available(self) -> bool:
        return not engine.is_offline("lightning")

    def get_latest(self, lat: float, lon: float) -> dict:
        if not self.is_available():
            raise ConnectionError("lightning adapter offline (simulated outage)")
        vals = engine.gen_lightning(lat, lon)
        vals["_meta"] = {
            "last_update_utc": datetime.now(timezone.utc).isoformat(),
            "latency_sec": self.latency_sec,
        }
        return vals
