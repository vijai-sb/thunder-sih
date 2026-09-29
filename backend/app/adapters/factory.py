"""Factory seam — swap mock -> live here later. Nothing else changes."""
from __future__ import annotations

from functools import lru_cache

from .lightning import MockLightningAdapter
from .nwp import MockModelAdapter
from .radar import MockRadarAdapter
from .satellite import MockSatelliteAdapter


@lru_cache
def get_radar_adapter() -> MockRadarAdapter:
    return MockRadarAdapter()


@lru_cache
def get_satellite_adapter() -> MockSatelliteAdapter:
    return MockSatelliteAdapter()


@lru_cache
def get_lightning_adapter() -> MockLightningAdapter:
    return MockLightningAdapter()


@lru_cache
def get_model_adapter() -> MockModelAdapter:
    return MockModelAdapter()


def all_adapters():
    return [get_radar_adapter(), get_satellite_adapter(), get_lightning_adapter(), get_model_adapter()]
