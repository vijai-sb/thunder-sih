import type { XAIExplanation } from '../lib/types';

function band(score: number): string {
  if (score >= 70) return 'HIGH';
  if (score >= 40) return 'MEDIUM';
  return 'LOW';
}

function pick(factors: XAIExplanation['factors'], keys: string[]) {
  let best: XAIExplanation['factors'][number] | null = null;
  for (const f of factors) {
    if (keys.some((k) => f.name.toLowerCase().includes(k)) && (!best || f.score > best.score)) best = f;
  }
  return best;
}

export default function FusedSignals({ xai }: { xai: XAIExplanation }) {
  const rows = [
    { label: 'RADAR', f: pick(xai.factors, ['radar']) },
    { label: 'LIGHTNING', f: pick(xai.factors, ['lightning']) },
    { label: 'SATELLITE', f: pick(xai.factors, ['cloud', 'satellite']) },
    { label: 'NWP / MODEL', f: pick(xai.factors, ['cape']) },
  ];
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <h2>Fused signals — PROTOTYPE FUSION EXPLANATION (not neural attribution)</h2>
      {rows.map((r) => (
        <div key={r.label} className="kv" title={r.f?.detail ?? 'no contributing signal in top factors'}>
          <span>{r.label}</span>
          <span>
            <span className={`pill ${(band(r.f?.score ?? 0) === 'HIGH' ? 'high' : band(r.f?.score ?? 0) === 'MEDIUM' ? 'moderate' : 'low') as string}`}>
              {band(r.f?.score ?? 0)}
            </span>{' '}
            <span className="mono small">{r.f ? `${r.f.name} ${r.f.score.toFixed(0)}` : '—'}</span>
          </span>
        </div>
      ))}
      <p style={{ marginTop: 8 }}>
        <b>PRIMARY TRIGGER — </b>
        {xai.summary}
      </p>
      <p className="small">
        Bands (≥70 HIGH / ≥40 MEDIUM) are display thresholds only — not calibrated, not trained
        feature attribution.
      </p>
    </div>
  );
}
