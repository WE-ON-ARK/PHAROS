import type { EventKindValue, TeamEvent } from "../types";
import { colors, radius } from "../theme";

const KIND_COLOR: Record<EventKindValue, string> = {
  mayday: colors.danger,
  flashover_warning: colors.warning,
  structural_collapse: colors.deepRed,
  new_victim: colors.blueLink,
  lost_contact: colors.stone,
  overload_alert: colors.yellow,
  evacuate: colors.warning,
  recovered: colors.lightGreen,
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
  const visible = [...events].reverse().slice(0, 10);

  return (
    <div style={{ padding: "16px 20px" }}>
      <div
        style={{
          fontSize: 12,
          color: colors.stone,
          marginBottom: 10,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
      >
        Event Feed ({events.length})
      </div>
      {visible.length === 0 ? (
        <div style={{ color: colors.stone, fontSize: 14 }}>No events yet</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {visible.map((ev) => {
            const color = KIND_COLOR[ev.kind];
            const label = KIND_LABEL[ev.kind];
            return (
              <div
                key={ev.event_id}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                  fontSize: 13,
                  lineHeight: 1.45,
                  padding: "6px 0",
                  borderBottom: `1px solid ${colors.hairlineDark}`,
                }}
              >
                <span
                  style={{
                    background: color,
                    color: colors.onPrimary,
                    padding: "2px 8px",
                    borderRadius: radius.full,
                    fontWeight: 700,
                    fontSize: 10,
                    whiteSpace: "nowrap",
                    letterSpacing: "0.04em",
                    flexShrink: 0,
                  }}
                >
                  {label}
                </span>
                <span style={{ color: colors.onDarkMute }}>{ev.message}</span>
                <span
                  style={{
                    color: colors.stone,
                    marginLeft: "auto",
                    whiteSpace: "nowrap",
                    flexShrink: 0,
                  }}
                >
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
