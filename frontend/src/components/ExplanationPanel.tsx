import type { XAIExplanation } from '../lib/types';

function bar(score: number): string {
  const full = Math.round(score / 10);
  return '█'.repeat(full) + '░'.repeat(10 - full);
}

export default function ExplanationPanel({ xai }: { xai: XAIExplanation }) {
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <h2>Why this alert? — top contributing factors (prototype, from live simulated state)</h2>
      {xai.factors.map((f) => (
        <div key={f.name} className="kv" title={f.detail}>
          <span>{f.name}</span>
          <span className="mono">
            {bar(f.score)} {f.score.toFixed(0)}
          </span>
        </div>
      ))}
      <p className="primary-signal" style={{ marginTop: 8 }}>
        <b>PRIMARY SIGNAL — </b>
        {xai.summary}
      </p>
      <p className="small">{xai.engine}</p>
    </div>
  );
}
