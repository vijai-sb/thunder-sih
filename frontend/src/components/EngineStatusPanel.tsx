export default function EngineStatusPanel() {
  return (
    <div className="card" style={{ marginTop: 12 }}>
      <h2>Nowcast engine — architecture status (no fake inference)</h2>
      <div className="kv">
        <span>Current prototype</span>
        <b>Deterministic simulated tracker</b>
      </div>
      <div className="kv">
        <span>Production ML slot</span>
        <b className="mono">ConvLSTM / U-Net (not connected)</b>
      </div>
      <div className="kv">
        <span>Current inference</span>
        <span className="pill sim">SIMULATED</span>
      </div>
      <div className="kv">
        <span>Status</span>
        <span className="pill degraded">PROTOTYPE</span>
      </div>
      <p className="small">
        Displayed tracks come from the simulated tracker only. No trained ConvLSTM/U-Net model is
        running in this prototype.
      </p>
    </div>
  );
}
