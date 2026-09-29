"""Single source of truth for Phase 1 data contracts.

Every observation carries Provenance so the UI/API can always
distinguish SIMULATED demo data from real feeds.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


RiskLevel = Literal["low", "moderate", "high", "severe"]
StormIntensity = Literal["weak", "moderate", "strong", "severe"]
SourceStatus = Literal["ok", "degraded", "offline"]
DataHealth = Literal["ok", "degraded", "offline"]


def risk_from_prob(p: float) -> RiskLevel:
    if p >= 75:
        return "severe"
    if p >= 50:
        return "high"
    if p >= 25:
        return "moderate"
    return "low"


class Location(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    region_name: str = "Delhi-NCR"


class Provenance(BaseModel):
    """Who / when / simulated? — attached to EVERY observation."""

    source: str = Field(..., description="e.g. radar, satellite, lightning, nwp, fusion, tracker")
    timestamp_utc: str = Field(default_factory=utcnow_iso)
    is_mock: bool = True
    is_live: bool = False
    data_mode: str = "mock"
    scenario_id: str = "normal"
    tick: int = 0
    freshness_sec: float = 0.0
    note: str = "SIMULATED DEMO DATA — not IMD/DWR/INSAT live observation"


class DataSourceMeta(BaseModel):
    source_id: str  # radar | satellite | lightning | nwp
    display_name: str
    connected: bool = True
    status: SourceStatus = "ok"
    last_update_utc: str = Field(default_factory=utcnow_iso)
    latency_sec: float = 0.0
    missing_data: bool = False
    message: str = ""


class RadarObservation(BaseModel):
    location: Location
    reflectivity_dbz: float
    velocity_ms: float
    echo_top_km: float
    vil_kgm2: float
    quality: str = "good"
    provenance: Provenance


class SatelliteObservation(BaseModel):
    location: Location
    cloud_top_temp_c: float
    cloud_top_height_km: float
    cloud_type: str
    ir_brightness: float
    wv_brightness: float
    quality: str = "good"
    provenance: Provenance


class LightningStrike(BaseModel):
    strike_id: str
    lat: float
    lon: float
    timestamp_utc: str
    peak_current_ka: float
    polarity: Literal["+", "-"] = "-"


class LightningObservation(BaseModel):
    location: Location
    strike_count_5min: int
    flash_rate_per_min: float
    avg_peak_current_ka: float
    strikes: List[LightningStrike] = []
    quality: str = "good"
    provenance: Provenance


class ModelObservation(BaseModel):
    """NWP / atmospheric model point (simulated)."""

    location: Location
    temp_c: float
    humidity_pct: float
    pressure_hpa: float
    wind_speed_ms: float
    wind_dir_deg: float
    cape_jkg: float
    cin_jkg: float
    shear_ms: float
    precip_mm: float
    quality: str = "good"
    provenance: Provenance


class StormCell(BaseModel):
    cell_id: str
    center_lat: float
    center_lon: float
    intensity: StormIntensity
    max_reflectivity_dbz: float
    speed_kmh: float
    direction_deg: float
    flash_rate_per_min: float
    lightning_jump: bool = False
    radius_km: float = 8.0
    provenance: Provenance


class AtmosphericState(BaseModel):
    """Fused common atmospheric state (Phase 1: heuristic fusion, NOT ML)."""

    location: Location
    timestamp_utc: str = Field(default_factory=utcnow_iso)
    scenario_id: str
    tick: int
    radar: Optional[RadarObservation] = None
    satellite: Optional[SatelliteObservation] = None
    lightning: Optional[LightningObservation] = None
    model: Optional[ModelObservation] = None
    storm_prob_pct: float
    lightning_prob_pct: float
    confidence_pct: float
    risk_level: RiskLevel
    data_health: DataHealth = "ok"
    missing_sources: List[str] = []
    fusion_basis: str = "heuristic-v0 (prototype, not validated — do not use operationally)"
    provenance: Provenance


class Prediction(BaseModel):
    location: Location
    timestamp_utc: str = Field(default_factory=utcnow_iso)
    horizon_min: int = 0
    storm_prob_pct: float
    lightning_prob_pct: float
    risk_level: RiskLevel
    confidence_pct: float
    basis: str = "heuristic-v0 nowcast (prototype, not validated)"
    provenance: Provenance


class Alert(BaseModel):
    alert_id: str
    created_at_utc: str = Field(default_factory=utcnow_iso)
    location: Location
    location_name: str
    risk_level: RiskLevel
    storm_prob_pct: float
    confidence_pct: float
    message: str
    status: Literal["active", "expired"] = "active"
    provenance: Provenance


class ScenarioInfo(BaseModel):
    scenario_id: str
    display_name: str
    description: str
    tick: int
    sim_time_utc: str
    is_mock: bool = True


# ---- Phase 2 (additive — Phase 1 contracts unchanged) ----
class TrackPoint(BaseModel):
    lat: float
    lon: float
    tick: int
    label: str = ""  # e.g. PREV, NOW, +30min


class ForecastPoint(BaseModel):
    horizon_min: int
    lat: float
    lon: float
    radius_km: float
    confidence_pct: float


class HazardZone(BaseModel):
    horizon_min: int  # 30 | 60 | 90
    center_lat: float
    center_lon: float
    radius_km: float
    label: str = "Prototype simulated nowcast — not calibrated"


class CellTrack(BaseModel):
    """Tracking result for one storm cell — same cell_id as StormCell."""

    cell_id: str
    intensity: StormIntensity
    current: TrackPoint
    previous: Optional[TrackPoint] = None
    speed_kmh: float
    direction_deg: float
    direction_cardinal: str = ""
    flash_rate_per_min: float
    flash_trend: str = "steady"  # increasing | steady | decreasing
    dbz_trend: str = "steady"
    growth_trend: str = "steady"  # intensifying | steady | decaying
    lightning_jump: bool = False
    forecast: List[ForecastPoint] = []
    hazards: List[HazardZone] = []
    provenance: Provenance


class RadarGridCell(BaseModel):
    lat: float
    lon: float
    dbz: float


# ---- Phase 3 (additive — intelligence layer; Phases 1–2 unchanged) ----
class JumpReport(BaseModel):
    cell_id: str
    current_rate: float
    previous_rate: float
    rate_of_change: float
    acceleration: float
    trend: str = "steady"  # increasing | steady | decreasing
    jump_detected: bool = False
    status: str = "none"  # jump | elevated | none
    detected_tick: Optional[int] = None
    threshold_note: str = "Configurable: abs>=2.0/min, rel>=10%, min 6.0/min (prototype)"


class CellRisk(BaseModel):
    cell_id: str
    prototype_score: float  # 0–100 Prototype Risk Score (NOT calibrated probability)
    storm_risk: RiskLevel
    lightning_risk: RiskLevel
    intensification: str = "steady"  # intensifying | steady | decaying
    confidence_label: str = "Prototype fusion confidence"
    confidence_pct: float
    engine: str = "Prototype Fusion Risk Engine (heuristic — not a trained ML model)"


class XAIFactor(BaseModel):
    name: str
    score: float  # 0–100 signal strength (prototype)
    detail: str


class XAIExplanation(BaseModel):
    cell_id: str
    factors: List[XAIFactor] = []
    summary: str
    engine: str = "Prototype explanation from live simulated state (not a trained model)"


class POI(BaseModel):
    poi_id: str
    name: str
    kind: str  # population | school | hospital | road | power | agri
    lat: float
    lon: float
    population: int = 0
    area_km2: float = 0.0


class ExposureSummary(BaseModel):
    horizon_min: int
    population: int = 0
    schools: int = 0
    hospitals: int = 0
    roads: int = 0
    power_sites: int = 0
    agri_km2: float = 0.0
    pois_affected: List[str] = []
    label: str = "Prototype exposure estimate (simulated demo POIs — not real infrastructure data)"


class TTIResult(BaseModel):
    cell_id: str
    target_name: str = ""
    minutes: Optional[float] = None
    label: str = "Prototype estimated time-to-impact (unvalidated constant-velocity)"


class HistoryPoint(BaseModel):
    tick: int
    flash_rate: float
    dbz: float
    risk_score: float
    jump: bool = False


class CellIntelligence(BaseModel):
    cell_id: str
    intensity: StormIntensity
    jump: JumpReport
    risk: CellRisk
    xai: XAIExplanation
    tti: TTIResult
    exposure_30: ExposureSummary
    exposure_60: ExposureSummary
    exposure_90: ExposureSummary
    history: List[HistoryPoint] = []
    provenance: Provenance


class IntelAlert(BaseModel):
    alert_id: str
    cell_id: str
    created_at_utc: str = Field(default_factory=utcnow_iso)
    severity: RiskLevel
    trigger: str
    message: str
    impact_min: Optional[float] = None
    status: str = "ACTIVE"  # ACTIVE | ACKNOWLEDGED | RESOLVED
    scenario_id: str = "normal"
    tick: int = 0
    provenance: Provenance
