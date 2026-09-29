export interface DemoStep {
  stage: string;
  scenario_id: string;
  tick: number;
  caption: string;
}

interface Props {
  plan: DemoStep[];
  index: number; // -1 = not started
  playing: boolean;
  busy: boolean;
  onPlay: () => void;
  onPause: () => void;
  onReset: () => void;
  onGoto: (i: number) => void;
}

export default function DemoMode({ plan, index, playing, busy, onPlay, onPause, onReset, onGoto }: Props) {
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <h2>Guided demo — simulation stages (not forecast times)</h2>
      <div className="row">
        {playing ? (
          <button onClick={onPause} disabled={busy}>Pause</button>
        ) : (
          <button className="primary" onClick={onPlay} disabled={busy}>Play demo</button>
        )}
        <button onClick={onReset} disabled={busy}>Reset demo</button>
        <span className="small">
          {index < 0 ? 'Not started — Play walks T+00 → T+90' : `DEMO STAGE ${plan[index]?.stage} — ${plan[index]?.caption} (simulation stage, not a forecast time)`}
        </span>
      </div>
      <div className="demo-progress" aria-hidden="true">
        <div
          className="demo-progress-fill"
          style={{ width: `${plan.length ? Math.round(((index + 1) / plan.length) * 100) : 0}%` }}
        />
      </div>
      <div className="row tl-steps" style={{ marginTop: 8 }} role="list">
        {plan.map((s, i) => (
          <button
            key={s.stage}
            role="listitem"
            onClick={() => onGoto(i)}
            disabled={busy}
            aria-current={i === index ? 'step' : undefined}
            title={`${s.stage}: ${s.caption} (${s.scenario_id} tick ${s.tick})`}
            className={i === index ? 'tl-active' : i < index ? 'tl-done' : undefined}
          >
            {i < index ? `✓ ${s.stage}` : s.stage}
          </button>
        ))}
      </div>
      <p className="small">
        Developing storm → lightning up → jump → HIGH risk → expanding impact → severe alert.
        Manual scenario / Simulate Event controls keep working during the demo.
      </p>
    </div>
  );
}
