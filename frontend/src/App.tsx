import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from './lib/api';
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
} from './lib/types';
import type { Lang } from './lib/i18n';
import NowcastMap, { DEFAULT_LAYERS, type LayerState } from './components/NowcastMap';
import TimelineScrubber, { HORIZONS } from './components/TimelineScrubber';
import ExplanationPanel from './components/ExplanationPanel';
import FusionStatusPanel from './components/FusionStatusPanel';
import LightningRiskPanel from './components/LightningRiskPanel';
import FusedSignals from './components/FusedSignals';
import UncertaintyPanel from './components/UncertaintyPanel';
import EngineStatusPanel from './components/EngineStatusPanel';
import IntensificationTimeline from './components/IntensificationTimeline';
import ImpactPanel from './components/ImpactPanel';
import AlertCenter from './components/AlertCenter';
import CitizenView from './components/CitizenView';
import DemoMode from './components/DemoMode';

const SCENARIO_IDS = [
  'normal',
  'developing',
  'intensifying',
  'severe-lightning',
] as const;

function fmtTime(iso?: string): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

const RISK_ORDER = ['low', 'moderate', 'high', 'severe'] as const;

function CommandStrip({
  scenario,
  cells,
  horizonMin,
  intel,
  intelAlerts,
}: {
  scenario: ScenarioInfo | null;
  cells: StormCell[];
  horizonMin: number;
  intel: CellIntelligence[];
  intelAlerts: IntelAlert[];
}) {
  const maxRisk = [...intel].sort(
    (a, b) => RISK_ORDER.indexOf(b.risk.storm_risk) - RISK_ORDER.indexOf(a.risk.storm_risk),
  )[0]?.risk.storm_risk ?? '—';
  const ttis = intel.map((c) => c.tti.minutes).filter((m): m is number => m != null);
  const minTti = ttis.length ? `${Math.min(...ttis)} min` : '—';
  const pop = intel.reduce((s, c) => s + c.exposure_60.population, 0);
  const active = intelAlerts.filter((a) => a.status === 'ACTIVE').length;
  return (
    <div className="card command-strip" style={{ marginTop: 12 }} aria-label="Current situation summary">
      <div className="cmd"><span>Conditions</span><b>{scenario ? `${scenario.display_name} · T${scenario.tick}` : '—'}</b></div>
      <div className="cmd"><span>Active storm</span><b>{cells.length} cell{cells.length === 1 ? '' : 's'}</b></div>
      <div className="cmd"><span>Nowcast</span><b>{horizonMin === 0 ? 'NOW' : `+${horizonMin} min`}</b></div>
      <div className="cmd hero"><span>Risk · prototype</span><b className={`pill ${maxRisk}`}>{String(maxRisk).toUpperCase()}</b></div>
      <div className="cmd hero"><span>Time to impact</span><b className="mono">{minTti}</b></div>
      <div className="cmd hero"><span>Impact (60-min)</span><b className="mono">{pop.toLocaleString()} exposed</b></div>
      <div className="cmd"><span>Alerts</span><b>{active} active</b></div>
    </div>
  );
}

export default function App() {
  const [scenario, setScenario] = useState<ScenarioInfo | null>(null);
  const [state, setState] = useState<AtmosphericState | null>(null);
  const [cells, setCells] = useState<StormCell[]>([]);
  const [tracks, setTracks] = useState<CellTrack[]>([]);
  const [radarGrid, setRadarGrid] = useState<RadarGridCell[]>([]);
  const [sources, setSources] = useState<DataSourceMeta[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [intel, setIntel] = useState<CellIntelligence[]>([]);
  const [intelAlerts, setIntelAlerts] = useState<IntelAlert[]>([]);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFetch, setLastFetch] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  // Phase 2 UI state
  const [layers, setLayers] = useState<LayerState>(DEFAULT_LAYERS);
  const [horizonMin, setHorizonMin] = useState(60);
  const [playing, setPlaying] = useState(false);
  const [selectedCellId, setSelectedCellId] = useState<string | null>(null);
  // Phase 4 UI state
  const [mode, setMode] = useState<'tech' | 'citizen'>('tech');
  const [lang, setLang] = useState<Lang>('en');
  const [pois, setPois] = useState<POI[]>([]);
  const [demoPlan, setDemoPlan] = useState<DemoStep[]>([]);
  const [demoIndex, setDemoIndex] = useState(-1);
  const [demoPlaying, setDemoPlaying] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const [banner, setBanner] = useState<IntelAlert | null>(null);
  const seenActive = useRef<Set<string>>(new Set());
  const timer = useRef<number | null>(null);
  const playTimer = useRef<number | null>(null);
  const demoTimer = useRef<number | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [h, sc, st, cl, so, al, tr, rg, it, ia, po, dp] = await Promise.all([
        api.health(),
        api.scenario(),
        api.state(),
        api.cells(),
        api.sources(),
        api.alerts(),
        api.tracks(),
        api.radarGrid(),
        api.intel(),
        api.intelAlerts(),
        api.pois(),
        api.demoPlan(),
      ]);
      if (!h.is_mock || !st.provenance?.is_mock || !tr.is_mock || !it.is_mock) {
        throw new Error('Provenance check failed: expected is_mock=true on all payloads.');
      }
      setBackendOk(true);
      setScenario(sc);
      setState(st);
      setCells(cl.cells);
      setSources(so.sources);
      setAlerts(al.alerts);
      setTracks(tr.tracks);
      setRadarGrid(rg.cells);
      setIntel(it.cells);
      setIntelAlerts(ia.alerts);
      setPois(po.pois);
      setDemoPlan(dp.steps);
      // alert visual escalation: banner on brand-new HIGH/SEVERE ACTIVE alerts
      const fresh = ia.alerts.filter(
        (a) => a.status === 'ACTIVE' && (a.severity === 'high' || a.severity === 'severe') && !seenActive.current.has(a.alert_id),
      );
      ia.alerts.forEach((a) => seenActive.current.add(a.alert_id));
      if (fresh.length > 0) {
        const top = fresh.sort((a, b) => (a.severity === 'severe' ? -1 : 1))[0];
        setBanner(top);
      }
      // keep selection valid across scenario switches
      setSelectedCellId((prev) =>
        prev && tr.tracks.some((t) => t.cell_id === prev) ? prev : null,
      );
      setLastFetch(new Date().toISOString());
      setError(null);
      const age = Date.now() - new Date(st.timestamp_utc).getTime();
      setStale(age > 120_000);
    } catch (e) {
      setBackendOk(false);
      setError(e instanceof Error ? e.message : String(e));
      if (lastFetch) {
        const age = Date.now() - new Date(lastFetch).getTime();
        setStale(age > 30_000);
      } else {
        setStale(true);
      }
    } finally {
      setLoading(false);
    }
  }, [lastFetch]);

  useEffect(() => {
    void fetchAll();
    timer.current = window.setInterval(() => void fetchAll(), 15000);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // play: step horizon NOW→90 loop
  useEffect(() => {
    if (!playing) {
      if (playTimer.current) window.clearInterval(playTimer.current);
      return;
    }
    playTimer.current = window.setInterval(() => {
      setHorizonMin((prev) => {
        const i = HORIZONS.indexOf(prev);
        return HORIZONS[(i + 1) % HORIZONS.length];
      });
    }, 1200);
    return () => {
      if (playTimer.current) window.clearInterval(playTimer.current);
    };
  }, [playing]);

  const gotoDemoStep = useCallback(async (i: number) => {
    const step = demoPlan[i];
    if (!step) return;
    setDemoBusy(true);
    try {
      setError(null);
      setPlaying(false);
      await api.demoGoto(step.scenario_id, step.tick);
      setDemoIndex(i);
      await fetchAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDemoBusy(false);
    }
  }, [demoPlan, fetchAll]);

  // guided demo playback: one stage every ~3s, manual controls stay live
  useEffect(() => {
    if (!demoPlaying) {
      if (demoTimer.current) window.clearInterval(demoTimer.current);
      return;
    }
    demoTimer.current = window.setInterval(() => {
      setDemoIndex((prev) => {
        const next = prev + 1;
        if (next >= demoPlan.length) {
          setDemoPlaying(false);
          return prev;
        }
        void gotoDemoStep(next);
        return next;
      });
    }, 3000);
    return () => {
      if (demoTimer.current) window.clearInterval(demoTimer.current);
    };
  }, [demoPlaying, demoPlan, gotoDemoStep]);

  const onDemoReset = async () => {
    setDemoPlaying(false);
    await gotoDemoStep(0);
  };

  const onScenario = async (id: string) => {
    try {
      setError(null);
      setPlaying(false);
      setHorizonMin(60);
      await api.setScenario(id);
      await fetchAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const onAdvance = async (steps = 1) => {
    try {
      setError(null);
      await api.advance(steps);
      await fetchAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const onToggleSource = async (id: string, currentlyConnected: boolean) => {
    try {
      if (currentlyConnected) await api.setSourceOffline(id);
      else await api.setSourceOnline(id);
      await fetchAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const toggleLayer = (k: keyof LayerState) =>
    setLayers((prev) => ({ ...prev, [k]: !prev[k] }));

  const selectedTrack = tracks.find((t) => t.cell_id === selectedCellId) ?? null;
  const selectedCell = cells.find((c) => c.cell_id === selectedCellId) ?? null;
  const selectedIntel = intel.find((c) => c.cell_id === selectedCellId) ?? null;
  const refreshIntelAlerts = useCallback(async () => {
    try {
      const ia = await api.intelAlerts();
      setIntelAlerts(ia.alerts);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  return (
    <div className="app">
      <div className="sim-banner">
        SIMULATED DEMO DATA — not IMD / DWR / INSAT live observations. Prototype confidence only; no
        operational accuracy claimed. Every payload carries <span className="mono">provenance.is_mock=true</span>.
      </div>

      <div className="header">
        <div>
          <h1>Storm Sentinel Command Center — SIH26072 (Simulated Prototype)</h1>
          <p>
            MULTI-SOURCE → FUSION → DETECTION → TRACKING → NOWCAST → LIGHTNING → RISK → WHY →
            TTI → IMPACT → ALERT → CITIZEN · Delhi-NCR (28.6139, 77.2090)
          </p>
        </div>
        <div className="row">
          <div className="row" role="group" aria-label="Dashboard mode">
            <button
              onClick={() => setMode('tech')}
              aria-pressed={mode === 'tech'}
              style={mode === 'tech' ? { borderColor: '#4da3ff', fontWeight: 700 } : undefined}
            >
              Technical
            </button>
            <button
              onClick={() => setMode('citizen')}
              aria-pressed={mode === 'citizen'}
              style={mode === 'citizen' ? { borderColor: '#4da3ff', fontWeight: 700 } : undefined}
            >
              Citizen View
            </button>
          </div>
          <span className={`pill ${backendOk === false ? 'offline' : backendOk ? 'ok' : ''}`}>
            {backendOk === null ? 'CHECKING…' : backendOk ? 'BACKEND OK' : 'BACKEND DOWN'}
          </span>
          <span className="pill sim">SIMULATED</span>
          <button onClick={() => void fetchAll()} disabled={loading} aria-label="Refresh all data">
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {mode === 'citizen' ? (
        <CitizenView intel={intel} lang={lang} onLang={setLang} onBack={() => setMode('tech')} />
      ) : (
      <>
      <CommandStrip
        scenario={scenario}
        cells={cells}
        horizonMin={horizonMin}
        intel={intel}
        intelAlerts={intelAlerts}
      />

      {banner && (
        <div className="alert-banner" role="alert">
          <b>⚠ {banner.severity.toUpperCase()} ALERT — {banner.cell_id}</b>
          <span> {banner.trigger} · impact {banner.impact_min != null ? `${banner.impact_min} min` : '—'}</span>
          <span className="row" style={{ marginLeft: 'auto' }}>
            <button
              onClick={() => {
                setSelectedCellId(banner.cell_id);
                setBanner(null);
              }}
            >
              View cell
            </button>
            <button onClick={() => setBanner(null)} aria-label="Dismiss alert banner">Dismiss</button>
          </span>
        </div>
      )}

      {error && (
        <div style={{ marginTop: 12 }} className="error">
          ERROR: {error}
          {'\n'}The dashboard kept the last good frame (if any) and flagged staleness instead of
          crashing. Check backend at http://localhost:8000/docs
        </div>
      )}
      {stale && !error && (
        <div style={{ marginTop: 12 }} className="stale">
          STALE DATA — last fetch {fmtTime(lastFetch ?? undefined)}. Auto-refresh every 15s.
        </div>
      )}
      {stale && error && (
        <div style={{ marginTop: 8 }} className="stale">
          STALE — showing last known values. Last good fetch: {fmtTime(lastFetch ?? undefined)}
        </div>
      )}

      <div className="card" style={{ marginTop: 12 }}>
        <h2>Interactive nowcast map — Leaflet (prototype simulated nowcast)</h2>
        <div className="row" style={{ marginBottom: 8 }}>
          <label className="small">
            <input type="checkbox" checked={layers.cells} onChange={() => toggleLayer('cells')} /> Storm Cells
          </label>
          <label className="small">
            <input type="checkbox" checked={layers.lightning} onChange={() => toggleLayer('lightning')} /> Lightning
          </label>
          <label className="small">
            <input type="checkbox" checked={layers.radar} onChange={() => toggleLayer('radar')} /> Radar/reflectivity (SIMULATED)
          </label>
          <label className="small">
            <input type="checkbox" checked={layers.f30} onChange={() => toggleLayer('f30')} /> 30-min forecast
          </label>
          <label className="small">
            <input type="checkbox" checked={layers.f60} onChange={() => toggleLayer('f60')} /> 60-min forecast
          </label>
          <label className="small">
            <input type="checkbox" checked={layers.f90} onChange={() => toggleLayer('f90')} /> 90-min forecast
          </label>
          <label className="small">
            <input type="checkbox" checked={layers.impact} onChange={() => toggleLayer('impact')} /> POIs + exposure (SIMULATED DEMO INFRASTRUCTURE)
          </label>
          <label className="small">
            <input type="checkbox" checked={layers.prob} onChange={() => toggleLayer('prob')} /> Storm probability (SIMULATED)
          </label>
        </div>
        {selectedIntel && (
          <div className="sel-chip" role="status" aria-label="Currently analyzed storm cell">
            <b>ANALYZING {selectedIntel.cell_id}</b>
            <span className={`pill ${selectedIntel.risk.storm_risk}`}>{selectedIntel.risk.storm_risk.toUpperCase()} · prototype score {selectedIntel.risk.prototype_score}</span>
            <span className="mono">
              {selectedTrack ? `${selectedTrack.direction_cardinal} ${selectedTrack.speed_kmh} km/h` : ''}
            </span>
            <span className="mono">⚡ {selectedIntel.jump.trend} {selectedIntel.jump.current_rate}/min</span>
            <span className="mono">
              TTI {selectedIntel.tti.minutes != null ? `${selectedIntel.tti.minutes} min` : '—'}
            </span>
            <a href="#why">↓ WHY THIS ALERT?</a>
          </div>
        )}
        <NowcastMap
          tracks={tracks}
          radarGrid={radarGrid}
          strikes={state?.lightning?.strikes ?? []}
          pois={pois}
          probByCell={Object.fromEntries(
            intel.map((c) => [c.cell_id, { band: c.risk.storm_risk, score: c.risk.prototype_score }]),
          )}
          layers={layers}
          horizonMin={horizonMin}
          selectedCellId={selectedCellId}
          escalatedCellId={banner?.cell_id ?? null}
          onSelectCell={setSelectedCellId}
        />
        <div className="map-legend" aria-label="Map legend">
          <span><i className="sw solid" /> CURRENT cell</span>
          <span><i className="sw path" /> ➤ PREDICTED path</span>
          <span><i className="sw hz30" /> 30 MIN zone</span>
          <span><i className="sw hz60" /> 60 MIN zone</span>
          <span><i className="sw hz90" /> 90 MIN zone</span>
          <span><i className="sw ltg" /> lightning activity</span>
          <span><i className="sw poi" /> simulated POI</span>
          <span><i className="sw prob" /> storm probability: LOW/MOD/HIGH/SEVERE (simulated, not calibrated)</span>
        </div>
        <p className="small">
          White ring = ALERT cell · dashed rings = hazard zones (prototype, uncalibrated) · heat grid =
          SIMULATED RADAR (not IMD) · pins = SIMULATED DEMO INFRASTRUCTURE · faint lines = fallback grid.
        </p>
      </div>

      <TimelineScrubber
        horizonMin={horizonMin}
        onChange={setHorizonMin}
        playing={playing}
        onPlayPause={() => setPlaying((p) => !p)}
        onReset={() => {
          setPlaying(false);
          setHorizonMin(0);
        }}
      />

      <div className="grid grid-2">
        <UncertaintyPanel horizonMin={horizonMin} />
        <EngineStatusPanel />
      </div>

      <DemoMode
        plan={demoPlan}
        index={demoIndex}
        playing={demoPlaying}
        busy={demoBusy || loading}
        onPlay={() => {
          if (demoIndex < 0 || demoIndex >= demoPlan.length - 1) void gotoDemoStep(0);
          setDemoPlaying(true);
        }}
        onPause={() => setDemoPlaying(false)}
        onReset={() => void onDemoReset()}
        onGoto={(i) => {
          setDemoPlaying(false);
          void gotoDemoStep(i);
        }}
      />

      {(selectedTrack || selectedCell) && (
        <div className="card" style={{ marginTop: 12, borderColor: '#4da3ff' }}>
          <h2>
            {selectedCellId} —{' '}
            {selectedTrack ? selectedTrack.intensity.toUpperCase() : selectedCell?.intensity.toUpperCase()} ·{' '}
            <span className="small">from live simulated tracking (click again on map to deselect)</span>
          </h2>
          <div className="grid grid-4">
            <div className="kv"><span>Location (NOW)</span><b className="mono">{selectedTrack ? `${selectedTrack.current.lat.toFixed(4)}, ${selectedTrack.current.lon.toFixed(4)}` : `${selectedCell?.center_lat.toFixed(3)}, ${selectedCell?.center_lon.toFixed(3)}`}</b></div>
            <div className="kv"><span>Movement</span><b>{selectedTrack ? `${selectedTrack.direction_cardinal} ${selectedTrack.speed_kmh} km/h @ ${selectedTrack.direction_deg}°` : `${selectedCell?.speed_kmh} km/h @ ${selectedCell?.direction_deg}°`}</b></div>
            <div className="kv"><span>Lightning</span><b className="mono">{selectedTrack ? `${selectedTrack.flash_rate_per_min}/min (${selectedTrack.flash_trend})` : `${selectedCell?.flash_rate_per_min}/min`}</b></div>
            <div className="kv"><span>Risk</span><span className={`pill ${state?.risk_level}`}>{state?.risk_level.toUpperCase()} ({state?.storm_prob_pct}%)</span></div>
          </div>
          {selectedTrack && (
            <>
              <div className="kv"><span>Previous (tick {selectedTrack.previous?.tick ?? '—'})</span><span className="mono">{selectedTrack.previous ? `${selectedTrack.previous.lat.toFixed(4)}, ${selectedTrack.previous.lon.toFixed(4)}` : 'genesis (tick 0)'}</span></div>
              <div className="kv"><span>Growth/decay</span><span>{selectedTrack.growth_trend} (dBZ {selectedTrack.dbz_trend}, flash {selectedTrack.flash_trend}){selectedTrack.lightning_jump ? ' · LIGHTNING JUMP' : ''}</span></div>
              <div className="kv"><span>Predicted +{horizonMin}min</span><span className="mono">{(() => { const f = selectedTrack.forecast.find((x) => x.horizon_min === horizonMin); return f ? `${f.lat.toFixed(4)}, ${f.lon.toFixed(4)} · r=${f.radius_km}km · conf ${f.confidence_pct}%` : 'NOW'; })()}</span></div>
              <button style={{ marginTop: 8 }} onClick={() => setSelectedCellId(null)}>Close panel</button>
            </>
          )}
        </div>
      )}

      {selectedIntel && (
        <>
          <div className="card" style={{ marginTop: 12, borderColor: '#e0a100' }}>
            <h2>
              Cell intelligence — {selectedIntel.cell_id} · Prototype Fusion Risk Engine (prototype,
              not a trained model)
            </h2>
            <div className="grid grid-4">
              <div className="kv"><span>Prototype risk score</span><b className="mono">{selectedIntel.risk.prototype_score}</b></div>
              <div className="kv"><span>Storm risk</span><span className={`pill ${selectedIntel.risk.storm_risk}`}>{selectedIntel.risk.storm_risk.toUpperCase()}</span></div>
              <div className="kv"><span>Lightning risk</span><span className={`pill ${selectedIntel.risk.lightning_risk}`}>{selectedIntel.risk.lightning_risk.toUpperCase()}</span></div>
              <div className="kv"><span>Prototype fusion confidence</span><span className="mono">{selectedIntel.risk.confidence_pct}%</span></div>
            </div>
            <div className="kv"><span>Lightning jump</span><span className={`pill ${selectedIntel.jump.jump_detected ? 'severe' : 'low'}`}>{selectedIntel.jump.jump_detected ? `DETECTED — ${selectedIntel.jump.current_rate}/min (was ${selectedIntel.jump.previous_rate}, tick ${selectedIntel.jump.detected_tick})` : `${selectedIntel.jump.status.toUpperCase()} — ${selectedIntel.jump.current_rate}/min`}</span></div>
            <p className="small">{selectedIntel.jump.threshold_note} · {selectedIntel.risk.engine}</p>
          </div>
          <div className="why-spotlight" id="why">
            <ExplanationPanel xai={selectedIntel.xai} />
          </div>
          <FusedSignals xai={selectedIntel.xai} />
          <IntensificationTimeline history={selectedIntel.history} />
          <div className="impact-feature">
            <ImpactPanel ci={selectedIntel} />
          </div>
        </>
      )}

      <LightningRiskPanel intel={intel} selectedId={selectedCellId} />

      <AlertCenter
        alerts={intelAlerts}
        intel={intel}
        fusionState={state?.data_health === 'ok' ? 'COMPLETE' : (state?.data_health ?? 'OFFLINE').toUpperCase()}
        onChanged={() => void refreshIntelAlerts()}
      />

      <div className="grid grid-2" style={{ marginTop: 12 }}>
        <div className="card">
          <h2>Scenario (deterministic)</h2>
          <div className="row">
            <select
              value={scenario?.scenario_id ?? 'developing'}
              onChange={(e) => void onScenario(e.target.value)}
            >
              {SCENARIO_IDS.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
            <button className="primary" onClick={() => void onAdvance(1)}>
              Simulate Event (+1 tick)
            </button>
            <button onClick={() => void onAdvance(3)}>+3 ticks</button>
            <button
              onClick={() =>
                api
                  .reset()
                  .then(() => fetchAll())
                  .catch((e) => setError(String(e)))
              }
            >
              Reset tick
            </button>
          </div>
          <div style={{ marginTop: 8 }}>
            <div className="kv">
              <span>current</span>
              <b>
                {scenario?.display_name ?? scenario?.scenario_id} · tick {scenario?.tick ?? '—'}
              </b>
            </div>
            <div className="kv">
              <span>description</span>
              <span>{scenario?.description ?? '—'}</span>
            </div>
            <div className="kv">
              <span>sim time</span>
              <span className="mono">{fmtTime(scenario?.sim_time_utc)}</span>
            </div>
            <div className="kv">
              <span>provenance</span>
              <span className="mono">
                {scenario?.is_mock ? 'is_mock=true' : '?'} · scenario={scenario?.scenario_id}
              </span>
            </div>
          </div>
          <p className="small">
            Simulate Event advances the deterministic clock: observations → lightning → cells →
            tracks → forecast path → hazard zones all update together. Timeline horizon ({horizonMin === 0 ? 'NOW' : `+${horizonMin}min`}) filters the map without changing sim state.
          </p>
        </div>

        <div className="card">
          <h2>Fused atmospheric state (heuristic-v0, not ML)</h2>
          {!state ? (
            <p className="small">No data yet — start backend and press Refresh.</p>
          ) : (
            <>
              <div className="kv">
                <span>storm probability</span>
                <b className="mono">{state.storm_prob_pct}%</b>
              </div>
              <div className="kv">
                <span>lightning probability</span>
                <b className="mono">{state.lightning_prob_pct}%</b>
              </div>
              <div className="kv">
                <span>risk</span>
                <span className={`pill ${state.risk_level}`}>{state.risk_level.toUpperCase()}</span>
              </div>
              <div className="kv">
                <span>confidence (prototype)</span>
                <span className="mono">{state.confidence_pct}%</span>
              </div>
              <div className="kv">
                <span>data health</span>
                <span className={`pill ${state.data_health}`}>{state.data_health}</span>
              </div>
              <div className="kv">
                <span>missing sources</span>
                <span className="mono">{state.missing_sources.join(', ') || 'none'}</span>
              </div>
              {state.missing_sources.length > 0 && (
                <div className="stale" style={{ marginTop: 6 }}>
                  DEGRADED — Prediction confidence reduced because {state.missing_sources.join(', ')}{' '}
                  data is unavailable. Fusion falls back to remaining sources.
                </div>
              )}
              <div className="kv">
                <span>lightning rate</span>
                <b className="mono">{state.lightning?.flash_rate_per_min ?? '—'}/min</b>
              </div>
              <div className="kv">
                <span>fused at</span>
                <span className="mono">{fmtTime(state.timestamp_utc)}</span>
              </div>
              <p className="small">{state.fusion_basis}</p>
            </>
          )}
        </div>
      </div>

      <FusionStatusPanel
        sources={sources}
        dataHealth={state?.data_health ?? 'offline'}
        missingSources={state?.missing_sources ?? []}
        lastUpdate={state?.timestamp_utc}
      />

      <div className="card" style={{ marginTop: 12 }}>
        <h2>Data sources (adapters — mock now, live-swappable)</h2>
        <div className="grid grid-4">
          {sources.map((s) => (
            <div key={s.source_id} className="card">
              <h2>{s.source_id}</h2>
              <div className="kv">
                <span>status</span>
                <span className={`pill ${s.status}`}>{s.connected ? 'OK' : 'OFFLINE'}</span>
              </div>
              <div className="kv">
                <span>latency</span>
                <span className="mono">{s.latency_sec}s</span>
              </div>
              <div className="kv">
                <span>updated</span>
                <span className="mono">{fmtTime(s.last_update_utc)}</span>
              </div>
              <div className="kv">
                <span>detail</span>
                <span>{s.display_name}</span>
              </div>
              <p className="small">{s.message}</p>
              <button onClick={() => void onToggleSource(s.source_id, s.connected)}>
                {s.connected ? `Simulate ${s.source_id} outage` : `Restore ${s.source_id}`}
              </button>
            </div>
          ))}
          {sources.length === 0 && <p className="small">No source data — backend unreachable?</p>}
        </div>
        {state && (
          <div className="grid grid-4" style={{ marginTop: 8 }}>
            <div className="kv">
              <span>radar dBZ</span>
              <b className="mono">{state.radar ? `${state.radar.reflectivity_dbz} dBZ` : 'MISSING'}</b>
            </div>
            <div className="kv">
              <span>satellite top</span>
              <b className="mono">
                {state.satellite ? `${state.satellite.cloud_top_temp_c}°C` : 'MISSING'}
              </b>
            </div>
            <div className="kv">
              <span>lightning 5-min</span>
              <b className="mono">
                {state.lightning ? `${state.lightning.strike_count_5min} strikes` : 'MISSING'}
              </b>
            </div>
            <div className="kv">
              <span>NWP CAPE</span>
              <b className="mono">{state.model ? `${state.model.cape_jkg} J/kg` : 'MISSING'}</b>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-2" style={{ marginTop: 12 }}>
        <div className="card">
          <h2>Storm cells ({cells.length}) — click row to inspect</h2>
          {cells.length === 0 ? (
            <p className="small">No cells in this scenario/tick (e.g. Normal at tick 0).</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Center</th>
                  <th>dBZ</th>
                  <th>Flash/min</th>
                  <th>Motion</th>
                  <th>Jump</th>
                </tr>
              </thead>
              <tbody>
                {cells.map((c) => (
                  <tr
                    key={c.cell_id}
                    onClick={() => setSelectedCellId((prev) => (prev === c.cell_id ? null : c.cell_id))}
                    style={{
                      cursor: 'pointer',
                      background: selectedCellId === c.cell_id ? '#1c2f55' : undefined,
                    }}
                  >
                    <td>
                      {c.cell_id} <span className={`pill ${c.intensity}`}>{c.intensity}</span>
                    </td>
                    <td className="mono">
                      {c.center_lat.toFixed(3)}, {c.center_lon.toFixed(3)}
                    </td>
                    <td className="mono">{c.max_reflectivity_dbz}</td>
                    <td className="mono">{c.flash_rate_per_min}</td>
                    <td className="mono">
                      {c.speed_kmh} km/h @ {c.direction_deg}°
                    </td>
                    <td>{c.lightning_jump ? 'JUMP' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="small">Cells use live simulated values (not hardcoded). Tracks add previous/forecast/trend.</p>
        </div>

        <div className="card">
          <h2>Alerts ({alerts.length}) — simulated, not official</h2>
          {alerts.length === 0 ? (
            <p className="small">No active alerts at current risk level. Try Intensifying + Simulate Event.</p>
          ) : (
            alerts.map((a) => (
              <div key={a.alert_id} className="card" style={{ marginBottom: 8 }}>
                <span className={`pill ${a.risk_level}`}>{a.risk_level.toUpperCase()}</span>{' '}
                <b>{a.alert_id}</b>
                <p>{a.message}</p>
                <p className="small mono">
                  {a.storm_prob_pct}% storm · {a.confidence_pct}% conf · {fmtTime(a.created_at_utc)}
                </p>
              </div>
            ))
          )}
          {state?.lightning && state.lightning.strikes.length > 0 && (
            <>
              <h2 style={{ marginTop: 12 }}>
                Latest strikes (sample {Math.min(8, state.lightning.strikes.length)}/
                {state.lightning.strike_count_5min} per 5 min)
              </h2>
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Lat/Lon</th>
                    <th>kA</th>
                  </tr>
                </thead>
                <tbody>
                  {state.lightning.strikes.slice(0, 8).map((s) => (
                    <tr key={s.strike_id}>
                      <td className="mono">{s.strike_id}</td>
                      <td className="mono">
                        {s.lat.toFixed(3)}, {s.lon.toFixed(3)}
                      </td>
                      <td className="mono">
                        {s.peak_current_ka}
                        {s.polarity}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      </div>

      <p className="small" style={{ marginTop: 12 }}>
        Timestamp (last good fetch): {fmtTime(lastFetch ?? undefined)} · Backend docs:{' '}
        <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
          localhost:8000/docs
        </a>{' '}
        · All values simulated. Fusion: 0.35·dBZ + 0.25·flash + 0.20·CAPE + 0.10·cold-top +
        0.10·shear, renormalized on missing sources. Map forecast: constant-velocity, uncalibrated.
      </p>
      <p className="storyline" aria-label="System story">
        DETECT → PREDICT → EXPLAIN → IMPACT → WARN · SIMULATED DATA · PROTOTYPE NOWCAST ·
        PROTOTYPE FUSION · PROTOTYPE RISK SCORE · PROTOTYPE TIME-TO-IMPACT · PROTOTYPE EXPOSURE
        ESTIMATE
      </p>
      </>
      )}
    </div>
  );
}
