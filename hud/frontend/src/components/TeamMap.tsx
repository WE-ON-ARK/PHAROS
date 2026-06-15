import type { PeerView } from "../types";
import { colors, radius, statusColor } from "../theme";

// Incident-map canvas dimensions (pixels)
const MAP_W = 500;
const MAP_H = 400;
// Building bounds in metres (must match sim/team.py constants)
const BLDG_W_M = 50.0;
// Scale: pixels per metre (y is mirrored: SVG y=0 is top, map y=0 is bottom)
const PX_PER_M = MAP_W / BLDG_W_M;

function toSvg(pos: [number, number]): [number, number] {
  return [pos[0] * PX_PER_M, MAP_H - pos[1] * PX_PER_M];
}

interface Props {
  peers: PeerView[];
}

export function TeamMap({ peers }: Props) {
  return (
    <div style={{ padding: "16px 24px" }}>
      <div
        style={{
          fontSize: 12,
          color: colors.stone,
          marginBottom: 12,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
      >
        Incident Map (50 × 40 m)
      </div>
      <svg
        viewBox={`0 0 ${MAP_W} ${MAP_H}`}
        width={MAP_W}
        height={MAP_H}
        style={{
          background: colors.surfaceElevated,
          borderRadius: radius.lg,
          border: `1px solid ${colors.hairlineDark}`,
          display: "block",
        }}
      >
        <rect
          x={0}
          y={0}
          width={MAP_W}
          height={MAP_H}
          fill="none"
          stroke={colors.hairlineStrong}
          strokeWidth={2}
        />
        <line x1={MAP_W / 2} y1={0} x2={MAP_W / 2} y2={MAP_H * 0.6} stroke={colors.hairlineStrong} strokeWidth={1} />
        <line x1={0} y1={MAP_H * 0.5} x2={MAP_W} y2={MAP_H * 0.5} stroke={colors.hairlineStrong} strokeWidth={1} />

        <line
          x1={10}
          y1={MAP_H - 10}
          x2={10 + 10 * PX_PER_M}
          y2={MAP_H - 10}
          stroke={colors.stone}
          strokeWidth={1.5}
        />
        <text x={10} y={MAP_H - 14} fill={colors.stone} fontSize={9}>
          10 m
        </text>

        {peers.map((pv) => {
          const [sx, sy] = toSvg(pv.position);
          const color = statusColor[pv.status] ?? colors.stone;
          return (
            <g key={pv.node_id}>
              {pv.status !== "ok" && <circle cx={sx} cy={sy} r={14} fill={color} opacity={0.18} />}
              <circle cx={sx} cy={sy} r={8} fill={color} opacity={0.95} />
              <text x={sx} y={sy - 12} textAnchor="middle" fill={color} fontSize={10} fontWeight={600}>
                {pv.node_id}
              </text>
              <text x={sx} y={sy + 20} textAnchor="middle" fill={colors.onDarkMute} fontSize={8}>
                {pv.status} · {(pv.cognitive_load * 100).toFixed(0)}%
              </text>
            </g>
          );
        })}
      </svg>

      <div style={{ display: "flex", gap: 14, marginTop: 12, flexWrap: "wrap" }}>
        {Object.entries(statusColor).map(([st, col]) => (
          <div key={st} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <div style={{ width: 9, height: 9, borderRadius: radius.full, background: col }} />
            <span style={{ color: colors.onDarkMute }}>{st}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
