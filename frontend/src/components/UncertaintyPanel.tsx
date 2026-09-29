const ROWS: { h: number; label: string; band: 'LOW' | 'MODERATE' | 'HIGH' }[] = [
  { h: 0, label: 'NOW', band: 'LOW' },
  { h: 30, label: '+30 MIN', band: 'LOW' },
  { h: 60, label: '+60 MIN', band: 'MODERATE' },
  { h: 90, label: '+90 MIN', band: 'MODERATE' },
  { h: 120, label: '+120 MIN', band: 'HIGH' },
  { h: 180, label: '+180 MIN', band: 'HIGH' },
];

export default function UncertaintyPanel({ horizonMin }: { horizonMin: number }) {
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <h2>Forecast uncertainty — prototype indicator, not calibrated</h2>
      {ROWS.map((r) => (
        <div key={r.h} className="kv">
          <span>
            {r.h === horizonMin ? '▶ ' : ''}
            {r.label}
          </span>
          <span className={`pill ${r.band === 'LOW' ? 'low' : r.band === 'MODERATE' ? 'moderate' : 'high'}`}>
            {r.band}
          </span>
        </div>
      ))}
      <p className="small">
        Uncertainty grows with lead time — hazard envelopes widen accordingly. Not a calibrated
        confidence interval; not operational.
      </p>
    </div>
  );
}
