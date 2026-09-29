# Storm Sentinel Command Center — SIH26072 Phase 4 (Judge-Ready, Simulated Prototype)

> **SIMULATED DEMO DATA — not IMD / DWR / INSAT live observations.**
> Prototype confidence only. No operational accuracy claimed. No trained ML model.

Phase 1 foundation + Phase 2 Leaflet nowcasting map + Phase 3 intelligence:
observe → detect → track → predict → explain → assess impact → warn.

## Structure

```
storm-nowcast/
  backend/
    app/
      models/schemas.py      # Pydantic contracts (single source of truth)
      sim/engine.py          # deterministic seeded simulation + scenarios
      adapters/              # radar/satellite/lightning/nwp + factory seam
      services/fusion.py     # heuristic-v0 fusion (NOT ML)
      routers/system.py      # health, scenario, sources
      routers/data.py        # observations, state, cells, prediction, alerts
      main.py                # FastAPI + CORS
    tests/test_phase1.py
  frontend/
    src/lib/types.ts         # TS mirrors of Pydantic contracts
    src/lib/api.ts           # typed client with error handling
    src/App.tsx              # Phase 1 dashboard (status, not polish)
```

## Run

Backend (port 8000):

```powershell
cd storm-nowcast\backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# docs: http://127.0.0.1:8000/docs
```

Frontend (port 5173, proxies /api → 8000):

```powershell
cd storm-nowcast\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
# app: http://127.0.0.1:5173/
```

Tests:

```powershell
cd storm-nowcast\backend
python -m pytest tests/test_phase1.py -v
```

Build check:

```powershell
cd storm-nowcast\frontend
npx tsc --noEmit
npm run build
```

## Scenarios

- `normal` — fair weather, 1 weak cell
- `developing` — 2 moderate cells (default)
- `intensifying` — 3 cells, strong
- `severe-lightning` — 4 cells, severe + jump flags

Same scenario+tick ⇒ same dBZ/flash/CAPE (sha256-seeded).
`POST /api/scenario/{id}` switches (resets tick).
`POST /api/scenario-advance?steps=N` = “Simulate Event”.
`POST /api/sources/{id}/offline|online` = fallback demo.

## Scientific honesty

Every payload has `provenance {source, timestamp_utc, is_mock:true, scenario_id, tick}`.
Fusion basis string: `heuristic-v0 (prototype, not validated — do not use operationally)`.
Alerts append `[SIMULATED DEMO — not an official IMD warning]`.
