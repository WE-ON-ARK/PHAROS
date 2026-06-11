import type { HudFrame } from "../types";

const MAX_BITS = 6;

interface BarProps {
  value: number;
  max: number;
  color: string;
  label: string;
  unit?: string;
}

function Bar({ value, max, color, label, unit = "" }: BarProps) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 3 }}>
        <span>{label}</span>
        <span style={{ fontVariantNumeric: "tabular-nums" }}>
          {value.toFixed(3)}{unit}
        </span>
      </div>
      <div style={{ background: "#1e293b", borderRadius: 3, height: 8 }}>
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            borderRadius: 3,
            transition: "width 0.1s ease",
          }}
        />
      </div>
    </div>
  );
}

function CogLoadBar({ value }: { value: number }) {
  const pct = Math.min(100, value * 100);
  const r = Math.round(pct * 2.55);
  const g = Math.round((100 - pct) * 2.55);
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 3 }}>
        <span>Cognitive Load</span>
        <span style={{ fontVariantNumeric: "tabular-nums" }}>{value.toFixed(3)}</span>
      </div>
      <div style={{ background: "#1e293b", borderRadius: 3, height: 12 }}>
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: `rgb(${r},${g},40)`,
            borderRadius: 3,
            transition: "width 0.1s ease",
          }}
        />
      </div>
    </div>
  );
}

interface Props {
  frame: HudFrame | null;
}

export function MetricsPanel({ frame }: Props) {
  if (!frame) {
    return (
      <div style={{ color: "#64748b", fontSize: 13, padding: 16 }}>
        Loading…
      </div>
    );
  }

  return (
    <div style={{ padding: "12px 16px" }}>
      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 12 }}>
        t = {frame.timestamp.toFixed(2)} s
      </div>

      <CogLoadBar value={frame.cognitive_load} />

      <Bar
        value={frame.gaze_entropy_hs}
        max={MAX_BITS}
        color="#818cf8"
        label="Gaze Entropy Hs"
        unit=" bits"
      />
      <Bar
        value={frame.gaze_entropy_ht}
        max={MAX_BITS}
        color="#6366f1"
        label="Gaze Entropy Ht"
        unit=" bits"
      />

      <div style={{ borderTop: "1px solid #1e293b", margin: "12px 0" }} />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 12 }}>
        <div>
          <div style={{ color: "#64748b" }}>Smoke</div>
          <div style={{ fontVariantNumeric: "tabular-nums", fontSize: 16, fontWeight: 600 }}>
            {(frame.smoke_density * 100).toFixed(1)}%
          </div>
        </div>
        <div>
          <div style={{ color: "#64748b" }}>Visibility</div>
          <div style={{ fontVariantNumeric: "tabular-nums", fontSize: 16, fontWeight: 600 }}>
            {frame.visibility.toFixed(1)} m
          </div>
        </div>
      </div>
    </div>
  );
}
