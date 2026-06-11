import type { EventKindValue, TeamEvent } from "../types";

const KIND_COLOR: Record<EventKindValue, string> = {
  mayday: "#ef4444",
  flashover_warning: "#f97316",
  structural_collapse: "#dc2626",
  new_victim: "#3b82f6",
  lost_contact: "#64748b",
  overload_alert: "#f59e0b",
  evacuate: "#f97316",
  recovered: "#22c55e",
};

const KIND_LABEL: Record<EventKindValue, string> = {
  mayday: "MAYDAY",
  flashover_warning: "FLASHOVER",
  structural_collapse: "COLLAPSE",
  new_victim: "VICTIM",
  lost_contact: "LOST",
  overload_alert: "OVERLOAD",
  evacuate: "EVACUATE",
  recovered: "RECOVERED",
};

interface Props {
  events: TeamEvent[];
}

export function EventFeed({ events }: Props) {
  // Show newest first, cap at 10
  const visible = [...events].reverse().slice(0, 10);

  return (
    <div style={{ padding: "12px 16px" }}>
      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8 }}>
        Event Feed ({events.length} total)
      </div>
      {visible.length === 0 ? (
        <div style={{ color: "#334155", fontSize: 12 }}>No events yet</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {visible.map((ev) => {
            const color = KIND_COLOR[ev.kind];
            const label = KIND_LABEL[ev.kind];
            return (
              <div
                key={ev.event_id}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 8,
                  fontSize: 11,
                  lineHeight: 1.4,
                  padding: "4px 0",
                  borderBottom: "1px solid #0f172a",
                }}
              >
                <span
                  style={{
                    background: color + "22",
                    color,
                    padding: "1px 5px",
                    borderRadius: 3,
                    fontWeight: 700,
                    fontSize: 9,
                    whiteSpace: "nowrap",
                    letterSpacing: "0.04em",
                    flexShrink: 0,
                  }}
                >
                  {label}
                </span>
                <span style={{ color: "#cbd5e1" }}>{ev.message}</span>
                <span style={{ color: "#475569", marginLeft: "auto", whiteSpace: "nowrap", flexShrink: 0 }}>
                  {ev.timestamp.toFixed(1)}s
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
