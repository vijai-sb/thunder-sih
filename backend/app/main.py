"""FastAPI entry — Phase 1 foundation. All data SIMULATED."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import data, demo, intel, system, tracks

app = FastAPI(title="Storm Nowcast API (Phase 3 — simulated)", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(tracks.router, prefix="/api")
app.include_router(intel.router, prefix="/api")
app.include_router(demo.router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "storm-nowcast",
        "phase": 3,
        "data_mode": "mock",
        "is_mock": True,
        "docs": "/docs",
        "note": "SIMULATED DEMO DATA — not IMD/DWR/INSAT live observation. No operational accuracy claimed.",
    }
