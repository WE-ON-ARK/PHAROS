import type { CameraMessage } from "../types";
import { colors, radius } from "../theme";
import { MetricsPanel } from "./MetricsPanel";
import { PriorityList } from "./PriorityList";

interface Props {
  message: CameraMessage | null;
  error: string | null;
}

function Badge({ detected }: { detected: boolean }) {
  return (
    <span
      style={{
        position: "absolute",
        top: 16,
        left: 16,
        padding: "4px 12px",
        borderRadius: radius.full,
        fontSize: 12,
        fontWeight: 600,
        letterSpacing: "0.04em",
        background: detected ? colors.lightGreen : colors.danger,
        color: colors.onPrimary,
      }}
    >
      {detected ? "TRACKING" : "NO FACE"}
    </span>
  );
}

export function CameraView({ message, error }: Props) {
  if (error) {
    return (
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
          padding: 32,
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 40 }}>📷</div>
        <div style={{ color: colors.onDark, fontSize: 18, fontWeight: 600 }}>
          Camera unavailable
        </div>
        <div style={{ color: colors.stone, fontSize: 14, maxWidth: 420 }}>{error}</div>
        <div style={{ color: colors.stone, fontSize: 13, maxWidth: 460 }}>
          Run the backend with camera access, or try the standalone{" "}
          <code style={{ color: colors.onDarkMute }}>python -m pharos.vision</code> window.
        </div>
      </div>
    );
  }

  if (!message) {
    return (
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: colors.stone,
          fontSize: 15,
        }}
      >
        Connecting to camera…
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
      {/* Camera view (full-bleed product mockup style on dark canvas) */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
          position: "relative",
        }}
      >
        <Badge detected={message.detected ?? false} />
        {message.image ? (
          <img
            src={message.image}
            alt="live camera"
            style={{
              maxWidth: "100%",
              maxHeight: "100%",
              borderRadius: radius.xl,
              border: `1px solid ${colors.hairlineDark}`,
            }}
          />
        ) : (
          <div style={{ color: colors.stone }}>No frame</div>
        )}
      </div>

      {/* Metrics column */}
      <div
        style={{
          width: 320,
          display: "flex",
          flexDirection: "column",
          borderLeft: `1px solid ${colors.hairlineDark}`,
          overflowY: "auto",
        }}
      >
        <div style={{ borderBottom: `1px solid ${colors.hairlineDark}` }}>
          <MetricsPanel frame={message.hud ?? null} />
        </div>
        <PriorityList frame={message.hud ?? null} />
      </div>
    </div>
  );
}
