import type { DataSourceMeta } from '../lib/types';

interface Props {
  sources: DataSourceMeta[];
  dataHealth: string;
  missingSources: string[];
  lastUpdate?: string;
}

const ORDER = [
  { id: 'radar', label: 'RADAR' },
  { id: 'satellite', label: 'SATELLITE' },
  { id: 'lightning', label: 'LIGHTNING' },
  { id: 'nwp', label: 'NWP / MODEL' },
];

function fmtTime(iso?: string): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleTimeString();
  } catch {
    return iso;
  }
}

export default function FusionStatusPanel({ sources, dataHealth, missingSources, lastUpdate }: Props) {
  const byId = new Map(sources.map((s) => [s.source_id, s]));
  const fusionState = dataHealth === 'ok' ? 'COMPLETE' : dataHealth.toUpperCase();
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <h2>Data fusion — multi-source atmospheric state (simulated)</h2>
      {ORDER.map((o) => {
        const s = byId.get(o.id);
        const ok = s ? s.connected : !missingSources.includes(o.id);
        return (
          <div key={o.id} className="kv">
            <span>{o.label}</span>
            <span className={`mono ${ok ? 'ok-text' : 'bad-text'}`}>
              ● {ok ? 'AVAILABLE' : 'MISSING'}
            </span>
          </div>
        );
      })}
      <div className="kv">
        <span>Fusion state</span>
        <span className={`pill ${dataHealth === 'ok' ? 'ok' : dataHealth === 'degraded' ? 'degraded' : 'offline'}`}>
          {fusionState}
        </span>
      </div>
      <div className="kv">
        <span>Last updated</span>
        <span className="mono">{fmtTime(lastUpdate)}</span>
      </div>
      <div className="kv">
        <span>Next update</span>
        <span className="mono">~10 min (intended cadence)</span>
      </div>
      <div className="kv">
        <span>Data status</span>
        <span className="pill sim">SIMULATED</span>
      </div>
      <p className="small">
        Prototype combines radar + satellite + lightning + NWP. Missing sources are excluded and
        confidence is reduced — see degraded notice above when active.
      </p>
    </div>
  );
}
