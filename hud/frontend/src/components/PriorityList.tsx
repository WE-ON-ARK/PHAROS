import type { HudMetrics } from "../types";
import { colors, hazardColor, radius } from "../theme";

interface Props {
  frame: HudMetrics | null;
}

export function PriorityList({ frame }: Props) {
  if (!frame || frame.ranked_scores.length === 0) {
    return <div style={{ color: colors.stone, fontSize: 14, padding: 20 }}>No hazards</div>;
  }

  const activeIds = new Set(frame.active_hazards.map((h) => h.id));

  return (
    <div style={{ padding: "12px 20px 20px" }}>
      <div
        style={{
          fontSize: 12,
          color: colors.stone,
          marginBottom: 10,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
      >
        Priority Queue
      </div>
      {frame.ranked_scores.map(([score, hid], i) => {
        const isActive = activeIds.has(hid);
        const kind =
          frame.active_hazards.find((h) => h.id === hid)?.kind ?? hid.toUpperCase();
        const color = hazardColor[kind] ?? colors.stone;
        return (
          <div
            key={hid}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "9px 12px",
              marginBottom: 6,
              borderRadius: radius.md,
              background: isActive ? colors.surfaceElevated : "transparent",
              border: isActive
                ? `1px solid ${color}`
                : `1px solid ${colors.hairlineDark}`,
              transition: "background 0.15s ease, border 0.15s ease",
            }}
          >
            <span
              style={{
                color: colors.stone,
                fontSize: 12,
                width: 14,
                textAlign: "right",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {i + 1}
            </span>
            <span
              style={{
                width: 9,
                height: 9,
                borderRadius: radius.full,
                background: color,
                flexShrink: 0,
              }}
            />
            <span
              style={{
                flex: 1,
                fontSize: 14,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? colors.onDark : colors.onDarkMute,
              }}
            >
              {hid}
            </span>
            <span
              style={{
                fontSize: 13,
                fontVariantNumeric: "tabular-nums",
                color: isActive ? colors.onDark : colors.stone,
              }}
            >
              {score.toFixed(3)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
