import type { CellIntelligence } from '../lib/types';

interface Props {
  intel: CellIntelligence[];
  selectedId: string | null;
}

export default function LightningRiskPanel({ intel, selectedId }: Props) {
  const ci =
    intel.find((c) => c.cell_id === selectedId) ??
    [...intel].sort((a, b) => b.jump.current_rate - a.jump.current_rate)[0];
  if (!ci) return null;
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <h2>
        Lightning risk — {ci.risk.lightning_risk.toUpperCase()} (simulated)
        {selectedId ? '' : ' · highest-activity cell shown'}
      </h2>
      <div className="kv">
        <span>Lightning</span>
        <b className="mono">{ci.jump.current_rate}/min</b>
      </div>
      <div className="kv">
        <span>Trend</span>
        <b className="mono">{ci.jump.trend.toUpperCase()}</b>
      </div>
      <div className="kv">
        <span>Jump</span>
        <span className={`pill ${ci.jump.jump_detected ? 'severe' : 'low'}`}>
          {ci.jump.jump_detected ? 'DETECTED' : ci.jump.status.toUpperCase()}
        </span>
      </div>
      <p className="small">From live simulated lightning state for {ci.cell_id} — not a calibrated forecast.</p>
    </div>
  );
}
