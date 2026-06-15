import type { HudMetrics } from "../types";
import { colors, radius } from "../theme";

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
    <div style={{ marginBottom: 12 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 13,
          marginBottom: 5,
          color: colors.onDarkMute,
        }}
      >
        <span>{label}</span>
        <span style={{ fontVariantNumeric: "tabular-nums", color: colors.onDark }}>
          {value.toFixed(3)}
          {unit}
        </span>
      </div>
      <div style={{ background: colors.surfaceElevated, borderRadius: radius.full, height: 8 }}>
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            borderRadius: radius.full,
            transition: "width 0.1s ease",
          }}
        />
      </div>
    </div>
  );
}

function loadColor(value: number): string {
  if (value >= 0.7) return colors.danger;
  if (value >= 0.4) return colors.warning;
  return colors.primary;
}

function CogLoadBar({ value }: { value: number }) {
  const pct = Math.min(100, value * 100);
  return (
    <div style={{ marginBottom: 14 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 13,
          marginBottom: 5,
          color: colors.onDarkMute,
        }}
      >
        <span>Cognitive Load</span>
        <span style={{ fontVariantNumeric: "tabular-nums", color: colors.onDark }}>
          {value.toFixed(3)}
        </span>
      </div>
      <div style={{ background: colors.surfaceElevated, borderRadius: radius.full, height: 12 }}>
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: loadColor(value),
            borderRadius: radius.full,
            transition: "width 0.1s ease",
          }}
        />
      </div>
    </div>
  );
}

interface Props {
  frame: HudMetrics | null;
}

export function MetricsPanel({ frame }: Props) {
  if (!frame) {
    return (
      <div style={{ color: colors.stone, fontSize: 14, padding: 20 }}>Loading…</div>
    );
  }

  return (
    <div style={{ padding: "16px 20px" }}>
      <div style={{ fontSize: 12, color: colors.stone, marginBottom: 14 }}>
        t = {frame.timestamp.toFixed(2)} s
      </div>

      <CogLoadBar value={frame.cognitive_load} />

      <Bar
        value={frame.gaze_entropy_hs}
        max={MAX_BITS}
        color={colors.onDark}
        label="Gaze Entropy Hs"
        unit=" bits"
      />
      <Bar
        value={frame.gaze_entropy_ht}
        max={MAX_BITS}
        color={colors.onDarkMute}
        label="Gaze Entropy Ht"
        unit=" bits"
      />

      <div style={{ borderTop: `1px solid ${colors.hairlineDark}`, margin: "14px 0" }} />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <div style={{ color: colors.stone, fontSize: 13 }}>Smoke</div>
          <div
            style={{
              fontVariantNumeric: "tabular-nums",
              fontSize: 24,
              fontWeight: 600,
              color: colors.onDark,
            }}
          >
            {(frame.smoke_density * 100).toFixed(1)}%
          </div>
        </div>
        <div>
          <div style={{ color: colors.stone, fontSize: 13 }}>Visibility</div>
          <div
            style={{
              fontVariantNumeric: "tabular-nums",
              fontSize: 24,
              fontWeight: 600,
              color: colors.onDark,
            }}
          >
            {frame.visibility.toFixed(1)} m
          </div>
        </div>
      </div>
    </div>
  );
}
