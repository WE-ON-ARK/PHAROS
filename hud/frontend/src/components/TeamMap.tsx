import type { PeerStatusKind, PeerView } from "../types";

// Incident-map canvas dimensions (pixels)
const MAP_W = 500;
const MAP_H = 400;
// Building bounds in metres (must match sim/team.py constants)
const BLDG_W_M = 50.0;
// Scale: pixels per metre (y is mirrored: SVG y=0 is top, map y=0 is bottom)
const PX_PER_M = MAP_W / BLDG_W_M;

const STATUS_COLOR: Record<PeerStatusKind, string> = {
  ok: "#22c55e",
  overload: "#f59e0b",
  distress: "#ef4444",
  down: "#dc2626",
  lost: "#64748b",
};

function toSvg(pos: [number, number]): [number, number] {
  return [pos[0] * PX_PER_M, MAP_H - pos[1] * PX_PER_M];
}

interface Props {
  peers: PeerView[];
}

export function TeamMap({ peers }: Props) {
  return (
    <div style={{ padding: "12px 16px" }}>
      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8 }}>
        Incident Map (50 × 40 m)
      </div>
      <svg
        viewBox={`0 0 ${MAP_W} ${MAP_H}`}
        width={MAP_W}
        height={MAP_H}
        style={{ background: "#0f172a", borderRadius: 6, border: "1px solid #1e293b", display: "block" }}
      >
        {/* Building outline */}
        <rect x={0} y={0} width={MAP_W} height={MAP_H} fill="none" stroke="#1e3a5f" strokeWidth={2} />

        {/* Room dividers — rough floor-plan grid */}
        <line x1={MAP_W / 2} y1={0} x2={MAP_W / 2} y2={MAP_H * 0.6} stroke="#1e3a5f" strokeWidth={1} />
        <line x1={0} y1={MAP_H * 0.5} x2={MAP_W} y2={MAP_H * 0.5} stroke="#1e3a5f" strokeWidth={1} />

        {/* Scale bar */}
        <line x1={10} y1={MAP_H - 10} x2={10 + 10 * PX_PER_M} y2={MAP_H - 10}
          stroke="#334155" strokeWidth={1.5} />
        <text x={10} y={MAP_H - 14} fill="#475569" fontSize={9}>10 m</text>

        {/* Peers */}
        {peers.map((pv) => {
          const [sx, sy] = toSvg(pv.position);
          const color = STATUS_COLOR[pv.status];
          return (
            <g key={pv.node_id}>
              {/* glow ring for non-OK status */}
              {pv.status !== "ok" && (
                <circle cx={sx} cy={sy} r={14} fill={color} opacity={0.18} />
              )}
              <circle cx={sx} cy={sy} r={8} fill={color} opacity={0.9} />
              <text
                x={sx}
                y={sy - 12}
                textAnchor="middle"
                fill={color}
                fontSize={10}
                fontWeight={600}
              >
                {pv.node_id}
              </text>
              <text
                x={sx}
                y={sy + 20}
                textAnchor="middle"
                fill="#94a3b8"
                fontSize={8}
              >
                {pv.status} · {(pv.cognitive_load * 100).toFixed(0)}%
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div style={{ display: "flex", gap: 12, marginTop: 8, flexWrap: "wrap" }}>
        {(Object.entries(STATUS_COLOR) as [PeerStatusKind, string][]).map(([st, col]) => (
          <div key={st} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11 }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: col }} />
            <span style={{ color: "#94a3b8" }}>{st}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
