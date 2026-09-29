"""Adapter interface — live providers implement this later without touching services."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    source_id: str = "base"
    display_name: str = "Base"
    latency_sec: float = 0.0

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def get_latest(self, lat: float, lon: float) -> dict:
        """Return raw simulated (later: real) values dict."""
        ...
