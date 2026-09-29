import type { HistoryPoint } from '../lib/types';

export default function IntensificationTimeline({ history }: { history: HistoryPoint[] }) {
  if (history.length === 0) return null;
  const maxFlash = Math.max(1, ...history.map((h) => h.flash_rate));
  const maxDbz = Math.max(1, ...history.map((h) => h.dbz));
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <h2>Storm intensification timeline — flash / radar / prototype risk score</h2>
      <table>
        <thead>
          <tr>
            <th>Tick</th>
            <th>Lightning/min</th>
            <th>Radar dBZ</th>
            <th>Risk score</th>
            <th>Jump</th>
          </tr>
        </thead>
        <tbody>
          {history.map((h) => (
            <tr key={h.tick}>
              <td className="mono">T{h.tick}</td>
              <td>
                <div className="tbar" style={{ width: `${Math.round((h.flash_rate / maxFlash) * 100)}%` }} />
                <span className="mono">{h.flash_rate}/min</span>
              </td>
              <td>
                <div className="tbar dbz" style={{ width: `${Math.round((h.dbz / maxDbz) * 100)}%` }} />
                <span className="mono">{h.dbz}</span>
              </td>
              <td className="mono">{h.risk_score}</td>
              <td>{h.jump ? 'JUMP' : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="small">
        Strengthening → lightning jump → increased prototype risk → larger predicted hazard. Values
        are simulated; risk is a prototype score, not a calibrated probability.
      </p>
    </div>
  );
}
