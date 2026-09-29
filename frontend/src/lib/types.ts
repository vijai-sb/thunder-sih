/* TypeScript mirrors of backend/app/models/schemas.py — keep in sync. */

export type RiskLevel = 'low' | 'moderate' | 'high' | 'severe';
export type StormIntensity = 'weak' | 'moderate' | 'strong' | 'severe';
export type SourceStatus = 'ok' | 'degraded' | 'offline';

export interface Location {
  lat: number;
  lon: number;
  region_name: string;
}

export interface Provenance {
  source: string;
  timestamp_utc: string;
  is_mock: boolean;
  is_live: boolean;
  data_mode: string;
  scenario_id: string;
  tick: number;
  freshness_sec: number;
  note: string;
}

export interface DataSourceMeta {
  source_id: string;
  display_name: string;
  connected: boolean;
  status: SourceStatus;
  last_update_utc: string;
  latency_sec: number;
  missing_data: boolean;
  message: string;
}

export interface RadarObservation {
  location: Location;
  reflectivity_dbz: number;
  velocity_ms: number;
  echo_top_km: number;
  vil_kgm2: number;
  quality: string;
  provenance: Provenance;
}

export interface SatelliteObservation {
  location: Location;
  cloud_top_temp_c: number;
  cloud_top_height_km: number;
  cloud_type: string;
  ir_brightness: number;
  wv_brightness: number;
  quality: string;
  provenance: Provenance;
}

export interface LightningStrike {
  strike_id: string;
  lat: number;
  lon: number;
  timestamp_utc: string;
  peak_current_ka: number;
  polarity: '+' | '-';
}

export interface LightningObservation {
  location: Location;
  strike_count_5min: number;
  flash_rate_per_min: number;
  avg_peak_current_ka: number;
  strikes: LightningStrike[];
  quality: string;
  provenance: Provenance;
}

export interface ModelObservation {
  location: Location;
  temp_c: number;
  humidity_pct: number;
  pressure_hpa: number;
  wind_speed_ms: number;
  wind_dir_deg: number;
  cape_jkg: number;
  cin_jkg: number;
  shear_ms: number;
  precip_mm: number;
  quality: string;
  provenance: Provenance;
}

export interface StormCell {
  cell_id: string;
  center_lat: number;
  center_lon: number;
  intensity: StormIntensity;
  max_reflectivity_dbz: number;
  speed_kmh: number;
  direction_deg: number;
  flash_rate_per_min: number;
  lightning_jump: boolean;
  radius_km: number;
  provenance: Provenance;
}

export interface AtmosphericState {
  location: Location;
  timestamp_utc: string;
  scenario_id: string;
  tick: number;
  radar: RadarObservation | null;
  satellite: SatelliteObservation | null;
  lightning: LightningObservation | null;
  model: ModelObservation | null;
  storm_prob_pct: number;
  lightning_prob_pct: number;
  confidence_pct: number;
  risk_level: RiskLevel;
  data_health: 'ok' | 'degraded' | 'offline';
  missing_sources: string[];
  fusion_basis: string;
  provenance: Provenance;
}

export interface Alert {
  alert_id: string;
  created_at_utc: string;
  location: Location;
  location_name: string;
  risk_level: RiskLevel;
  storm_prob_pct: number;
  confidence_pct: number;
  message: string;
  status: 'active' | 'expired';
  provenance: Provenance;
}

export interface ScenarioInfo {
  scenario_id: string;
  display_name: string;
  description: string;
  tick: number;
  sim_time_utc: string;
  is_mock: boolean;
}

/* Phase 2 (additive — mirrors backend tracking schemas, Phase 1 unchanged) */
export interface TrackPoint {
  lat: number;
  lon: number;
  tick: number;
  label: string;
}

export interface ForecastPoint {
  horizon_min: number;
  lat: number;
  lon: number;
  radius_km: number;
  confidence_pct: number;
}

export interface HazardZone {
  horizon_min: number;
  center_lat: number;
  center_lon: number;
  radius_km: number;
  label: string;
}

export interface CellTrack {
  cell_id: string;
  intensity: StormIntensity;
  current: TrackPoint;
  previous: TrackPoint | null;
  speed_kmh: number;
  direction_deg: number;
  direction_cardinal: string;
  flash_rate_per_min: number;
  flash_trend: 'increasing' | 'steady' | 'decreasing';
  dbz_trend: string;
  growth_trend: string;
  lightning_jump: boolean;
  forecast: ForecastPoint[];
  hazards: HazardZone[];
  provenance: Provenance;
}

export interface RadarGridCell {
  lat: number;
  lon: number;
  dbz: number;
}

export interface POI {
  poi_id: string;
  name: string;
  kind: 'population' | 'school' | 'hospital' | 'road' | 'power' | 'agri';
  lat: number;
  lon: number;
  population?: number;
  area_km2?: number;
}

export interface DemoStep {
  stage: string;
  scenario_id: string;
  tick: number;
  caption: string;
}

/* Phase 3 (additive — mirrors backend intelligence schemas) */
export interface JumpReport {
  cell_id: string;
  current_rate: number;
  previous_rate: number;
  rate_of_change: number;
  acceleration: number;
  trend: string;
  jump_detected: boolean;
  status: 'jump' | 'elevated' | 'none';
  detected_tick: number | null;
  threshold_note: string;
}

export interface CellRisk {
  cell_id: string;
  prototype_score: number;
  storm_risk: RiskLevel;
  lightning_risk: RiskLevel;
  intensification: string;
  confidence_label: string;
  confidence_pct: number;
  engine: string;
}

export interface XAIFactor {
  name: string;
  score: number;
  detail: string;
}

export interface XAIExplanation {
  cell_id: string;
  factors: XAIFactor[];
  summary: string;
  engine: string;
}

export interface ExposureSummary {
  horizon_min: number;
  population: number;
  schools: number;
  hospitals: number;
  roads: number;
  power_sites: number;
  agri_km2: number;
  pois_affected: string[];
  label: string;
}

export interface TTIResult {
  cell_id: string;
  target_name: string;
  minutes: number | null;
  label: string;
}

export interface HistoryPoint {
  tick: number;
  flash_rate: number;
  dbz: number;
  risk_score: number;
  jump: boolean;
}

export interface CellIntelligence {
  cell_id: string;
  intensity: StormIntensity;
  jump: JumpReport;
  risk: CellRisk;
  xai: XAIExplanation;
  tti: TTIResult;
  exposure_30: ExposureSummary;
  exposure_60: ExposureSummary;
  exposure_90: ExposureSummary;
  history: HistoryPoint[];
  provenance: Provenance;
}

export interface IntelAlert {
  alert_id: string;
  cell_id: string;
  created_at_utc: string;
  severity: RiskLevel;
  trigger: string;
  message: string;
  impact_min: number | null;
  status: 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED';
  scenario_id: string;
  tick: number;
}
