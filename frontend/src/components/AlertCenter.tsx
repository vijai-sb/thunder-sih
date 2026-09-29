import { useState } from 'react';
import { api } from '../lib/api';
import type { CellIntelligence, IntelAlert } from '../lib/types';

interface Props {
  alerts: IntelAlert[];
  intel: CellIntelligence[];
  fusionState: string;
  onChanged: () => void;
}

export default function AlertCenter({ alerts, intel, fusionState, onChanged }: Props) {
  const exposureByCell = new Map(intel.map((c) => [c.cell_id, c.exposure_60]));
  const [filter, setFilter] = useState<'ACTIVE' | 'ALL'>('ACTIVE');
  const [busy, setBusy] = useState<string | null>(null);
  const shown = filter === 'ACTIVE' ? alerts.filter((a) => a.status === 'ACTIVE') : alerts;

  const act = async (id: string, kind: 'ack' | 'resolve') => {
    setBusy(id);
    try {
      if (kind === 'ack') await api.ackAlert(id);
      else await api.resolveAlert(id);
      onChanged();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="card" style={{ marginTop: 12 }}>
      <h2>Alert center — prototype fusion alerts (SQLite persisted)</h2>
      <div className="row" style={{ marginBottom: 8 }}>
        <button onClick={() => setFilter('ACTIVE')} style={filter === 'ACTIVE' ? { borderColor: '#4da3ff' } : undefined}>
          Active ({alerts.filter((a) => a.status === 'ACTIVE').length})
        </button>
        <button onClick={() => setFilter('ALL')} style={filter === 'ALL' ? { borderColor: '#4da3ff' } : undefined}>
          All ({alerts.length})
        </button>
        <span className="small">Severity · location · trigger · time · prototype TTI · status</span>
      </div>
      {shown.length === 0 ? (
        <p className="small">No {filter === 'ACTIVE' ? 'active' : ''} alerts. Try Intensifying/Severe or Simulate Event on Developing.</p>
      ) : (
        shown.map((a) => {
          const expo = exposureByCell.get(a.cell_id);
          return (
          <div key={a.alert_id} className="card" style={{ marginBottom: 8 }}>
            <span className={`pill ${a.severity}`}>{a.severity.toUpperCase()}</span> <b>{a.alert_id}</b>{' '}
            <span className={`pill ${a.status === 'ACTIVE' ? 'high' : 'low'}`}>{a.status}</span>
            <p>{a.message}</p>
            <p className="small mono">
              cell {a.cell_id} · trigger: {a.trigger} · impact {a.impact_min != null ? `${a.impact_min} min` : '—'} ·{' '}
              {new Date(a.created_at_utc).toLocaleString()} · prototype fusion confidence
            </p>
            <p className="small mono">
              exposure: {expo ? `${expo.population.toLocaleString()} population · ${expo.schools} schools · ${expo.hospitals} hospitals` : '— (cell not in current intel)'} ·{' '}
              fusion: {fusionState}
            </p>
            <p className="small"><b>SIMULATED DEMO — NOT AN OFFICIAL IMD WARNING</b></p>
            {a.status === 'ACTIVE' && (
              <div className="row">
                <button disabled={busy === a.alert_id} onClick={() => void act(a.alert_id, 'ack')}>Acknowledge</button>
                <button disabled={busy === a.alert_id} onClick={() => void act(a.alert_id, 'resolve')}>Resolve</button>
              </div>
            )}
            {a.status === 'ACKNOWLEDGED' && (
              <div className="row">
                <button disabled={busy === a.alert_id} onClick={() => void act(a.alert_id, 'resolve')}>Resolve</button>
              </div>
            )}
          </div>
          );
        })
      )}
    </div>
  );
}
