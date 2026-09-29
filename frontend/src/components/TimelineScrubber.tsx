interface Props {
  horizonMin: number;
  onChange: (h: number) => void;
  playing: boolean;
  onPlayPause: () => void;
  onReset: () => void;
}

export const HORIZONS = [0, 15, 30, 45, 60, 75, 90, 120, 150, 180];

export function horizonLabel(h: number): string {
  return h === 0 ? 'NOW' : `+${h} min`;
}

export default function TimelineScrubber({ horizonMin, onChange, playing, onPlayPause, onReset }: Props) {
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <h2>Nowcast timeline — NOW → +180 min (prototype simulated nowcast, not calibrated)</h2>
      <div className="row">
        <button onClick={onPlayPause}>{playing ? 'Pause' : 'Play'}</button>
        <button onClick={onReset}>Reset to NOW</button>
        <input
          type="range"
          min={0}
          max={HORIZONS.length - 1}
          step={1}
          value={HORIZONS.indexOf(horizonMin)}
          onChange={(e) => onChange(HORIZONS[Number(e.target.value)])}
          style={{ flex: 1 }}
          aria-label="Nowcast horizon scrubber"
        />
        <b className="mono">{horizonLabel(horizonMin)}</b>
      </div>
      <div className="row tl-steps" style={{ marginTop: 8 }}>
        {HORIZONS.map((h) => (
          <button
            key={h}
            onClick={() => onChange(h)}
            className={h === horizonMin ? 'tl-active' : undefined}
            aria-current={h === horizonMin ? 'step' : undefined}
          >
            {horizonLabel(h)}
          </button>
        ))}
      </div>
      <p className="small">
        Map now shows NOW{horizonMin > 0 ? ` → +${horizonMin} min forecast path + hazard zones to +${horizonMin} min` : ' (select +30/+60/+90/+120/+150/+180 to reveal predicted path and hazard zones)'} ·
        storm position, path, zones and impact update together. Constant-velocity, uncalibrated.
      </p>
    </div>
  );
}
