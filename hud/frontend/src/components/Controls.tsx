import type { Scenario } from "../types";

interface Props {
  scenario: Scenario;
  onScenarioChange: (s: Scenario) => void;
  isPlaying: boolean;
  onPlayPause: () => void;
  onRestart: () => void;
  frameIdx: number;
  totalFrames: number;
  onSeek: (idx: number) => void;
  speed: number;
  onSpeedChange: (s: number) => void;
}

const SPEEDS = [0.5, 1, 2, 4];

export function Controls({
  scenario,
  onScenarioChange,
  isPlaying,
  onPlayPause,
  onRestart,
  frameIdx,
  totalFrames,
  onSeek,
  speed,
  onSpeedChange,
}: Props) {
  const btnBase: React.CSSProperties = {
    padding: "5px 12px",
    borderRadius: 4,
    border: "1px solid #334155",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 500,
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "8px 16px",
        background: "#0f172a",
        borderTop: "1px solid #1e293b",
        flexWrap: "wrap",
      }}
    >
      {/* Scenario toggle */}
      <div style={{ display: "flex", gap: 4 }}>
        {(["a", "b"] as Scenario[]).map((s) => (
          <button
            key={s}
            onClick={() => onScenarioChange(s)}
            style={{
              ...btnBase,
              background: scenario === s ? "#6366f1" : "#1e293b",
              color: scenario === s ? "#fff" : "#94a3b8",
              borderColor: scenario === s ? "#6366f1" : "#334155",
            }}
          >
            Scenario {s.toUpperCase()}
          </button>
        ))}
      </div>

      <div style={{ width: 1, height: 24, background: "#334155" }} />

      {/* Playback controls */}
      <button
        onClick={onRestart}
        style={{ ...btnBase, background: "#1e293b", color: "#94a3b8" }}
      >
        ⏮
      </button>
      <button
        onClick={onPlayPause}
        style={{ ...btnBase, background: "#1e293b", color: "#f1f5f9", minWidth: 60 }}
      >
        {isPlaying ? "⏸ Pause" : "▶ Play"}
      </button>

      {/* Timeline scrubber */}
      <input
        type="range"
        min={0}
        max={Math.max(0, totalFrames - 1)}
        value={frameIdx}
        onChange={(e) => onSeek(Number(e.target.value))}
        style={{ flex: 1, minWidth: 80, accentColor: "#6366f1" }}
      />
      <span style={{ fontSize: 11, color: "#64748b", fontVariantNumeric: "tabular-nums", minWidth: 60 }}>
        {frameIdx + 1} / {totalFrames}
      </span>

      {/* Speed selector */}
      <div style={{ display: "flex", gap: 3, alignItems: "center" }}>
        <span style={{ fontSize: 11, color: "#64748b" }}>Speed:</span>
        {SPEEDS.map((s) => (
          <button
            key={s}
            onClick={() => onSpeedChange(s)}
            style={{
              ...btnBase,
              padding: "3px 7px",
              background: speed === s ? "#334155" : "transparent",
              color: speed === s ? "#f1f5f9" : "#64748b",
              borderColor: speed === s ? "#475569" : "transparent",
            }}
          >
            {s}×
          </button>
        ))}
      </div>
    </div>
  );
}
