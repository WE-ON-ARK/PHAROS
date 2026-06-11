import type { HudFrame } from "../types";

const KIND_COLOR: Record<string, string> = {
  VICTIM: "#ef4444",
  ESCAPE_ROUTE: "#22c55e",
  FIRE_POINT: "#f97316",
  STRUCTURAL: "#94a3b8",
  TEAMMATE: "#3b82f6",
};

interface Props {
  frame: HudFrame | null;
}

export function PriorityList({ frame }: Props) {
  if (!frame || frame.ranked_scores.length === 0) {
    return <div style={{ color: "#64748b", fontSize: 13, padding: 16 }}>No hazards</div>;
  }

  const activeIds = new Set(frame.active_hazards.map((h) => h.id));

  return (
    <div style={{ padding: "8px 12px" }}>
      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8, letterSpacing: "0.05em" }}>
        PRIORITY QUEUE
      </div>
      {frame.ranked_scores.map(([score, hid], i) => {
        const isActive = activeIds.has(hid);
        const kind = frame.active_hazards.find((h) => h.id === hid)?.kind ?? hid.toUpperCase();
        const color = KIND_COLOR[kind] ?? "#94a3b8";
        return (
          <div
            key={hid}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "6px 8px",
              marginBottom: 4,
              borderRadius: 4,
              background: isActive ? color + "22" : "transparent",
              border: isActive ? `1px solid ${color}66` : "1px solid transparent",
              transition: "background 0.15s ease, border 0.15s ease",
            }}
          >
            <span style={{ color: "#64748b", fontSize: 11, width: 14, textAlign: "right" }}>
              {i + 1}
            </span>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: color,
                flexShrink: 0,
              }}
            />
            <span style={{ flex: 1, fontSize: 12, fontWeight: isActive ? 600 : 400 }}>
              {hid}
            </span>
            <span
              style={{
                fontSize: 11,
                fontVariantNumeric: "tabular-nums",
                color: isActive ? "#f1f5f9" : "#64748b",
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
