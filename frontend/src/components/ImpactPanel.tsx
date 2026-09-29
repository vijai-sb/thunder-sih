import type { CellIntelligence } from '../lib/types';

function interpretation(ci: CellIntelligence): string {
  const jump = ci.jump.jump_detected;
  const high = ci.risk.storm_risk === 'high' || ci.risk.storm_risk === 'severe';
  const exposed = ci.exposure_60.population > 0 || ci.exposure_60.schools > 0 || ci.exposure_60.hospitals > 0;
  if (jump && high && exposed)
    return 'Rapidly increasing lightning activity combined with strong radar intensity indicates an intensifying convective cell. Several simulated population and infrastructure points fall within the projected hazard area.';
  if (jump && high)
    return 'Lightning jump with elevated prototype risk indicates an intensifying cell; simulated exposure in the hazard area is currently limited but the track should be watched.';
  if (high)
    return 'Elevated prototype risk with strong simulated signals; lightning is not jumping yet but conditions favor intensification.';
  if (ci.risk.storm_risk === 'moderate')
    return 'Gradually organizing simulated convection at moderate prototype risk; monitor lightning trend for a jump signal.';
  return 'No significant simulated thunderstorm signal at this cell.';
}

export default function ImpactPanel({ ci }: { ci: CellIntelligence }) {
  const e = ci.exposure_60;
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <h2>
        Projected impact — {ci.cell_id} · SIMULATED DEMO EXPOSURE
      </h2>
      <div className="impact-hero">
        <div><span>Population</span><b>{e.population.toLocaleString()}</b></div>
        <div><span>Time to impact</span><b>{ci.tti.minutes != null ? `${ci.tti.minutes} min` : '—'}</b></div>
        <div><span>Schools</span><b>{e.schools}</b></div>
        <div><span>Hospitals</span><b>{e.hospitals}</b></div>
      </div>
      <div className="kv">
        <span>Risk</span>
        <span className={`pill ${ci.risk.storm_risk}`}>{ci.risk.storm_risk.toUpperCase()}</span>
      </div>
      <div className="kv">
        <span>Lightning</span>
        <span className="mono">
          {ci.jump.current_rate}/min ({ci.jump.trend})
        </span>
      </div>
      <div className="kv">
        <span>Lightning jump</span>
        <span className={`pill ${ci.jump.jump_detected ? 'severe' : 'low'}`}>
          {ci.jump.jump_detected ? `DETECTED (tick ${ci.jump.detected_tick})` : ci.jump.status.toUpperCase()}
        </span>
      </div>
      <div className="kv">
        <span>Prototype estimated time-to-impact</span>
        <b className="mono">
          {ci.tti.minutes != null ? `${ci.tti.minutes} min → ${ci.tti.target_name}` : '— (no demo POI ahead)'}
        </b>
      </div>
      <div className="grid grid-4" style={{ marginTop: 8 }}>
        <div className="kv"><span>Population</span><b className="mono">{e.population.toLocaleString()}</b></div>
        <div className="kv"><span>Schools</span><b className="mono">{e.schools}</b></div>
        <div className="kv"><span>Hospitals</span><b className="mono">{e.hospitals}</b></div>
        <div className="kv"><span>Roads</span><b className="mono">{e.roads}</b></div>
      </div>
      <div className="grid grid-4">
        <div className="kv"><span>Power sites</span><b className="mono">{e.power_sites}</b></div>
        <div className="kv"><span>Agri area</span><b className="mono">{e.agri_km2} km²</b></div>
        <div className="kv"><span>Zone</span><span className="mono">60-min</span></div>
        <div className="kv"><span>30 / 90-min pop</span><span className="mono">{ci.exposure_30.population.toLocaleString()} / {ci.exposure_90.population.toLocaleString()}</span></div>
      </div>
      <p style={{ marginTop: 8 }}>{interpretation(ci)}</p>
      <p className="small">
        {e.label} {ci.tti.label}
      </p>
    </div>
  );
}
