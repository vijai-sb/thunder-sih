/* Typed API client with strict error handling — proves invalid/missing/stale cases. */
import type {
  Alert,
  AtmosphericState,
  CellIntelligence,
  CellTrack,
  DataSourceMeta,
  DemoStep,
  IntelAlert,
  POI,
  RadarGridCell,
  ScenarioInfo,
  StormCell,
} from './types';

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    });
  } catch (e) {
    throw new Error(`Network/unavailable: ${path} — backend not reachable (${String(e)})`);
  }
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`API ${res.status} on ${path}: ${body.slice(0, 300)}`);
  }
  try {
    return (await res.json()) as T;
  } catch {
    throw new Error(`Invalid JSON response from ${path}`);
  }
}

export const api = {
  health: () => req<{ status: string; is_mock: boolean; timestamp_utc: string }>('/api/health'),
  scenario: () => req<ScenarioInfo>('/api/scenario'),
  scenarios: () =>
    req<{ scenarios: { scenario_id: string; display_name: string; description: string }[] }>('/api/scenarios'),
  setScenario: (id: string) => req<ScenarioInfo>(`/api/scenario/${id}`, { method: 'POST' }),
  advance: (steps = 1) => req<ScenarioInfo>(`/api/scenario-advance?steps=${steps}`, { method: 'POST' }),
  reset: () => req<ScenarioInfo>('/api/scenario-reset', { method: 'POST' }),
  state: (lat = 28.6139, lon = 77.209) =>
    req<AtmosphericState>(`/api/state?lat=${lat}&lon=${lon}`),
  cells: () => req<{ cells: StormCell[]; count: number; scenario_id: string; tick: number; is_mock: boolean }>('/api/cells'),
  sources: () => req<{ sources: DataSourceMeta[]; is_mock: boolean }>('/api/sources'),
  alerts: () => req<{ alerts: Alert[]; count: number; is_mock: boolean }>('/api/alerts'),
  setSourceOffline: (id: string) => req<unknown>(`/api/sources/${id}/offline`, { method: 'POST' }),
  setSourceOnline: (id: string) => req<unknown>(`/api/sources/${id}/online`, { method: 'POST' }),
  tracks: () =>
    req<{ tracks: CellTrack[]; count: number; scenario_id: string; tick: number; horizons_min: number[]; is_mock: boolean }>(
      '/api/tracks',
    ),
  radarGrid: (n = 7, step = 0.05) =>
    req<{ cells: RadarGridCell[]; count: number; is_mock: boolean; note: string }>(
      `/api/radar-grid?n=${n}&step_deg=${step}`,
    ),
  intel: () =>
    req<{ cells: CellIntelligence[]; count: number; alerts_synced: number; scenario_id: string; tick: number; is_mock: boolean }>(
      '/api/intel/cells',
    ),
  intelAlerts: (status?: string) =>
    req<{ alerts: IntelAlert[]; count: number; is_mock: boolean }>(
      status ? `/api/intel/alerts?status=${status}` : '/api/intel/alerts',
    ),
  ackAlert: (id: string) => req<IntelAlert>(`/api/intel/alerts/${id}/ack`, { method: 'POST' }),
  resolveAlert: (id: string) => req<IntelAlert>(`/api/intel/alerts/${id}/resolve`, { method: 'POST' }),
  demoPlan: () =>
    req<{ steps: DemoStep[]; count: number; is_mock: boolean; note: string }>('/api/demo/plan'),
  demoGoto: (scenario_id: string, tick: number) =>
    req<{ scenario_id: string; tick: number }>(`/api/demo/goto`, {
      method: 'POST',
      body: JSON.stringify({ scenario_id, tick }),
    }),
  pois: () => req<{ pois: POI[]; count: number; is_mock: boolean; note: string }>('/api/pois'),
};
