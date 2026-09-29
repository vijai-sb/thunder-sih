import { useState } from 'react';
import L from 'leaflet';
import { Circle, CircleMarker, MapContainer, Marker, Polyline, Popup, TileLayer, Tooltip } from 'react-leaflet';
import type { CellTrack, LightningStrike, POI, RadarGridCell } from '../lib/types';

export interface LayerState {
  cells: boolean;
  lightning: boolean;
  radar: boolean;
  f30: boolean;
  f60: boolean;
  f90: boolean;
  impact: boolean;
  prob: boolean;
}

export const DEFAULT_LAYERS: LayerState = {
  cells: true,
  lightning: true,
  radar: true,
  f30: true,
  f60: true,
  f90: true,
  impact: true,
  prob: true,
};

const PROB_COLOR: Record<string, string> = {
  low: '#4da3ff',
  moderate: '#e0a100',
  high: '#e06c1b',
  severe: '#e5484d',
};

export interface CellProb {
  band: string;
  score: number;
}

const INTENSITY_COLOR: Record<string, string> = {
  weak: '#2fbf71',
  moderate: '#e0a100',
  strong: '#e06c1b',
  severe: '#e5484d',
};

const POI_COLOR: Record<string, string> = {
  population: '#4da3ff',
  school: '#9b5de5',
  hospital: '#ff5d8f',
  road: '#9aa7bd',
  power: '#f5a623',
  agri: '#2fbf71',
};

function dbzColor(dbz: number): string {
  if (dbz >= 55) return '#e5484d';
  if (dbz >= 45) return '#e06c1b';
  if (dbz >= 35) return '#e0a100';
  if (dbz >= 25) return '#2fbf71';
  return '#4da3ff';
}

function haversineKm(aLat: number, aLon: number, bLat: number, bLon: number): number {
  const r = 6371;
  const dLat = ((bLat - aLat) * Math.PI) / 180;
  const dLon = ((bLon - aLon) * Math.PI) / 180;
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos((aLat * Math.PI) / 180) * Math.cos((bLat * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(h));
}

// Aggregate strikes into grid cells so activity (not every point) dominates.
interface StrikeCluster {
  lat: number;
  lon: number;
  count: number;
  peakKa: number;
}

function clusterStrikes(strikes: LightningStrike[]): StrikeCluster[] {
  const cell = 0.04;
  const map = new Map<string, StrikeCluster>();
  for (const s of strikes.slice(0, 60)) {
    const key = `${Math.floor(s.lat / cell)}:${Math.floor(s.lon / cell)}`;
    const cur = map.get(key);
    if (cur) {
      cur.count += 1;
      cur.peakKa = Math.max(cur.peakKa, s.peak_current_ka);
      cur.lat = (cur.lat + s.lat) / 2;
      cur.lon = (cur.lon + s.lon) / 2;
    } else {
      map.set(key, { lat: s.lat, lon: s.lon, count: 1, peakKa: s.peak_current_ka });
    }
  }
  return [...map.values()].slice(0, 14);
}

function bearingDeg(aLat: number, aLon: number, bLat: number, bLon: number): number {
  const dLon = ((bLon - aLon) * Math.PI) / 180;
  const y = Math.sin(dLon) * Math.cos((bLat * Math.PI) / 180);
  const x =
    Math.cos((aLat * Math.PI) / 180) * Math.sin((bLat * Math.PI) / 180) -
    Math.sin((aLat * Math.PI) / 180) * Math.cos((bLat * Math.PI) / 180) * Math.cos(dLon);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

function arrowIcon(angleDeg: number, color: string) {
  return L.divIcon({
    className: 'path-arrow',
    html: `<span style="display:inline-block;transform:rotate(${Math.round(angleDeg)}deg);color:${color};font-size:15px;line-height:1">➤</span>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

interface Props {
  tracks: CellTrack[];
  radarGrid: RadarGridCell[];
  strikes: LightningStrike[];
  pois: POI[];
  probByCell: Record<string, CellProb>;
  layers: LayerState;
  horizonMin: number; // selected timeline horizon: 0,15,...,90
  selectedCellId: string | null;
  escalatedCellId: string | null;
  onSelectCell: (id: string | null) => void;
}

function hazardVisible(h: number, layers: LayerState): boolean {
  if (h === 30) return layers.f30;
  if (h === 60) return layers.f60;
  if (h === 90) return layers.f90;
  return false;
}

// Light lat/lon graticule so the map stays readable if tiles fail.
const GRATICULE_LATS = [28.45, 28.55, 28.65, 28.75, 28.85];
const GRATICULE_LONS = [76.95, 77.05, 77.15, 77.25, 77.35, 77.45];

export default function NowcastMap({
  tracks,
  radarGrid,
  strikes,
  pois,
  probByCell,
  layers,
  horizonMin,
  selectedCellId,
  escalatedCellId,
  onSelectCell,
}: Props) {
  const center: [number, number] = [28.6139, 77.209];
  const strikeClusters = clusterStrikes(strikes);
  const dimOthers = selectedCellId != null;
  const [tileErrors, setTileErrors] = useState(0);
  const tileFallback = tileErrors >= 4;

  const hz60 = tracks.flatMap((t) => t.hazards.filter((h) => h.horizon_min === 60));

  const poiStatus = (p: POI): { inside: boolean; distKm: number } => {
    let best = Infinity;
    for (const h of hz60) {
      const d = haversineKm(p.lat, p.lon, h.center_lat, h.center_lon) - h.radius_km;
      if (d < best) best = d;
    }
    if (!Number.isFinite(best)) return { inside: false, distKm: Infinity };
    return { inside: best <= 0, distKm: best <= 0 ? 0 : Math.round(best * 10) / 10 };
  };

  return (
    <MapContainer center={center} zoom={10} style={{ height: 'clamp(360px, 55vh, 500px)', width: '100%', borderRadius: 10 }}>
      {!tileFallback && (
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          eventHandlers={{
            tileerror: () => setTileErrors((n) => n + 1),
          }}
        />
      )}
      {GRATICULE_LATS.map((la) => (
        <Polyline
          key={`grat-la-${la}`}
          positions={[[la, 76.9], [la, 77.5]]}
          pathOptions={{ color: '#3a4763', weight: 1, opacity: 0.5, dashArray: '2 5' }}
        />
      ))}
      {GRATICULE_LONS.map((lo) => (
        <Polyline
          key={`grat-lo-${lo}`}
          positions={[[28.4, lo], [28.9, lo]]}
          pathOptions={{ color: '#3a4763', weight: 1, opacity: 0.5, dashArray: '2 5' }}
        />
      ))}
      {tileFallback && (
        <Circle
          center={center}
          radius={1000}
          pathOptions={{ color: '#9aa7bd', weight: 0, fillOpacity: 0 }}
        >
          <Tooltip permanent direction="center">
            OFFLINE MAP FALLBACK — schematic view, tiles unreachable. Storm vectors remain live.
          </Tooltip>
        </Circle>
      )}

      {layers.radar &&
        radarGrid.map((g, i) => (
          <CircleMarker
            key={`radar-${i}`}
            center={[g.lat, g.lon]}
            radius={11}
            pathOptions={{
              color: dbzColor(g.dbz),
              fillColor: dbzColor(g.dbz),
              fillOpacity: (g.dbz >= 35 ? 0.26 : 0.1) * (dimOthers ? 0.55 : 1),
              weight: 0,
            }}
          >
            <Tooltip sticky>
              SIMULATED RADAR — {g.dbz} dBZ
              <br />
              {g.lat.toFixed(3)}, {g.lon.toFixed(3)}
            </Tooltip>
          </CircleMarker>
        ))}

      {tracks.map((t) => {
        const color = INTENSITY_COLOR[t.intensity] ?? '#4da3ff';
        const isSel = selectedCellId === t.cell_id;
        const isEsc = escalatedCellId === t.cell_id;
        const dimmed = dimOthers && !isSel;
        // forecast path clipped to selected horizon (CURRENT vs PREDICTED distinction)
        const pathPts: [number, number][] = [
          [t.current.lat, t.current.lon],
          ...t.forecast
            .filter((f) => f.horizon_min <= Math.max(horizonMin, 0))
            .map((f) => [f.lat, f.lon] as [number, number]),
        ];
        const ghost = t.forecast.find((f) => f.horizon_min === horizonMin);
        // directional arrows along the predicted path (every other segment)
        const arrows = pathPts.slice(1).map((pt, i) => {
          const prev = pathPts[i];
          const mid: [number, number] = [(prev[0] + pt[0]) / 2, (prev[1] + pt[1]) / 2];
          return { mid, angle: bearingDeg(prev[0], prev[1], pt[0], pt[1]), i };
        }).filter((a) => isSel || isEsc || a.i % 2 === 0);

        return (
          <div key={t.cell_id}>
            {layers.cells && (
              <>
                {t.previous && (
                  <Polyline
                    positions={[
                      [t.previous.lat, t.previous.lon],
                      [t.current.lat, t.current.lon],
                    ]}
                    pathOptions={{ color: '#ffffff', weight: 2, opacity: dimmed ? 0.3 : 0.85 }}
                  />
                )}
                {isSel && (
                  <Circle
                    center={[t.current.lat, t.current.lon]}
                    radius={(t.intensity === 'weak' ? 5000 : 8000) + 2500}
                    pathOptions={{ color: '#ffffff', weight: 2, opacity: 0.7, fillOpacity: 0 }}
                  />
                )}
                <Circle
                  center={[t.current.lat, t.current.lon]}
                  radius={t.intensity === 'weak' ? 5000 : 8000}
                  pathOptions={{
                    color: isEsc ? '#ffffff' : color,
                    fillColor: color,
                    fillOpacity: isSel ? 0.5 : dimmed ? 0.1 : 0.28,
                    weight: isEsc ? 5 : isSel ? 4 : 2,
                    opacity: dimmed ? 0.55 : 1,
                  }}
                  eventHandlers={{ click: () => onSelectCell(isSel ? null : t.cell_id) }}
                >
                  <Tooltip permanent direction="top" offset={[0, -8]}>
                    {isEsc ? `⚠ ${t.cell_id} · ALERT` : `${t.cell_id} · ${t.intensity}`}
                  </Tooltip>
                  <Popup>
                    <b>{t.cell_id}</b> — {t.intensity.toUpperCase()}
                    <br />
                    Movement: {t.direction_cardinal} {t.speed_kmh} km/h @ {t.direction_deg}°
                    <br />
                    Lightning: {t.flash_rate_per_min}/min ({t.flash_trend})
                    <br />
                    Growth: {t.growth_trend}
                    <br />
                    Click row below for full panel.
                  </Popup>
                </Circle>
              </>
            )}

            {/* predicted trajectory (dashed = PREDICTED), prominent for the analyzed cell */}
            {pathPts.length > 1 && (
              <Polyline
                positions={pathPts}
                pathOptions={{
                  color,
                  weight: isSel || isEsc ? 4 : 2.5,
                  dashArray: '8 5',
                  opacity: dimmed ? 0.35 : 0.95,
                }}
              />
            )}
            {pathPts.length > 1 &&
              arrows.map((a) => (
                <Marker
                  key={`${t.cell_id}-arrow-${a.i}`}
                  position={a.mid}
                  icon={arrowIcon(a.angle, dimmed ? '#9aa7bd' : color)}
                  interactive={false}
                  keyboard={false}
                />
              ))}
            {/* ghost marker at selected horizon = storm visibly moves with scrubber */}
            {ghost && horizonMin > 0 && (
              <CircleMarker
                center={[ghost.lat, ghost.lon]}
                radius={isSel ? 10 : 7}
                pathOptions={{ color, fillColor: '#ffffff', fillOpacity: 0.9, weight: 3, opacity: dimmed ? 0.5 : 1 }}
              >
                <Tooltip>
                  PREDICTED +{horizonMin}min — {t.cell_id}
                  <br />
                  conf {ghost.confidence_pct}% (prototype, uncalibrated)
                </Tooltip>
              </CircleMarker>
            )}

            {t.hazards
              .filter((h) => h.horizon_min <= Math.max(horizonMin, 0))
              .filter((h) => hazardVisible(h.horizon_min, layers))
              .map((h) => (
                <Circle
                  key={`${t.cell_id}-hz-${h.horizon_min}`}
                  center={[h.center_lat, h.center_lon]}
                  radius={h.radius_km * 1000}
                  pathOptions={{
                    color: h.horizon_min === 30 ? '#e0a100' : h.horizon_min === 60 ? '#e06c1b' : '#e5484d',
                    fillOpacity: isEsc ? 0.16 : isSel ? 0.12 : dimmed ? 0.04 : 0.08,
                    weight: isSel || isEsc ? 2.5 : 1.25,
                    dashArray: '4 4',
                    opacity: dimmed ? 0.5 : 1,
                  }}
                >
                  {isSel ? (
                    <Tooltip permanent direction="center" opacity={1}>
                      {h.horizon_min} MIN
                    </Tooltip>
                  ) : (
                    <Tooltip sticky>
                      {h.horizon_min}-min hazard zone — {t.cell_id}
                      <br />
                      Prototype simulated nowcast — not calibrated
                    </Tooltip>
                  )}
                </Circle>
              ))}

            {layers.prob && probByCell[t.cell_id] && (
              <Circle
                key={`${t.cell_id}-prob`}
                center={[t.current.lat, t.current.lon]}
                radius={(t.intensity === 'weak' ? 5000 : 8000) + 1200}
                pathOptions={{
                  color: PROB_COLOR[probByCell[t.cell_id].band] ?? '#9aa7bd',
                  weight: 2,
                  dashArray: '2 4',
                  fillOpacity: 0,
                  opacity: dimmed ? 0.45 : 0.9,
                }}
              >
                {isSel ? (
                  <Tooltip permanent direction="bottom" offset={[0, 6]} opacity={1}>
                    {t.cell_id} · {probByCell[t.cell_id].band.toUpperCase()} ({probByCell[t.cell_id].score})
                  </Tooltip>
                ) : (
                  <Tooltip sticky>
                    STORM PROBABILITY (SIMULATED) — {t.cell_id}: {probByCell[t.cell_id].band.toUpperCase()}{' '}
                    {probByCell[t.cell_id].score}
                    <br />
                    Simulated prototype probability — NOT CALIBRATED, not operational
                  </Tooltip>
                )}
              </Circle>
            )}
          </div>
        );
      })}

      {layers.lightning &&
        strikeClusters.map((c, i) => (
          <CircleMarker
            key={`ltg-${i}`}
            center={[c.lat, c.lon]}
            radius={c.count > 1 ? 4 + Math.min(5, c.count) : 2.5}
            pathOptions={{
              color: '#ffd60a',
              fillColor: '#ffd60a',
              fillOpacity: c.count > 1 ? 0.65 : 0.4,
              weight: 0,
              opacity: dimOthers ? 0.5 : 1,
            }}
          >
            <Tooltip sticky>
              Lightning activity — {c.count} strike{c.count === 1 ? '' : 's'} here (peak {c.peakKa}kA)
              <br />
              Trend shown in cell panel, not per point
            </Tooltip>
          </CircleMarker>
        ))}

      {layers.impact &&
        pois.map((p) => {
          const st = poiStatus(p);
          const color = POI_COLOR[p.kind] ?? '#9aa7bd';
          const exposed = st.inside;
          return (
            <CircleMarker
              key={p.poi_id}
              center={[p.lat, p.lon]}
              radius={exposed ? (p.kind === 'population' ? 7 : 5.5) : p.kind === 'population' ? 4 : 3}
              pathOptions={{
                color,
                fillColor: color,
                fillOpacity: exposed ? 0.95 : 0.35,
                weight: exposed ? 2 : 1,
                opacity: dimOthers && !exposed ? 0.5 : 1,
              }}
            >
              <Tooltip>
                <b>{p.name}</b> — {p.kind}
                <br />
                SIMULATED DEMO INFRASTRUCTURE
                <br />
                {st.inside
                  ? 'Inside 60-min hazard zone'
                  : Number.isFinite(st.distKm)
                    ? `${st.distKm} km from 60-min hazard edge`
                    : 'No hazard computed'}
              </Tooltip>
            </CircleMarker>
          );
        })}
    </MapContainer>
  );
}
