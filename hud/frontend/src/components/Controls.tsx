import type { Scenario } from "../types";
import { colors, radius } from "../theme";

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
  const pill: React.CSSProperties = {
    padding: "8px 16px",
    borderRadius: radius.full,
    border: `1px solid ${colors.hairlineDark}`,
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 600,
    background: colors.surfaceElevated,
    color: colors.onDarkMute,
    fontFamily: "inherit",
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        padding: "14px 24px",
        background: colors.canvasDark,
        borderTop: `1px solid ${colors.hairlineDark}`,
        flexWrap: "wrap",
      }}
    >
      {/* Scenario toggle — cobalt accent marks the active condition */}
      <div style={{ display: "flex", gap: 6 }}>
        {(["a", "b"] as Scenario[]).map((s) => (
          <button
            key={s}
            onClick={() => onScenarioChange(s)}
            style={{
              ...pill,
              background: scenario === s ? colors.primary : colors.surfaceElevated,
              color: scenario === s ? colors.onPrimary : colors.onDarkMute,
              borderColor: scenario === s ? colors.primary : colors.hairlineDark,
            }}
          >
            Scenario {s.toUpperCase()}
          </button>
        ))}
      </div>

      <div style={{ width: 1, height: 28, background: colors.hairlineDark }} />

      {/* Playback controls — Play is the white primary pill */}
      <button onClick={onRestart} style={{ ...pill, padding: "8px 14px" }}>
        ⏮
      </button>
      <button
        onClick={onPlayPause}
        style={{
          ...pill,
          minWidth: 96,
          background: colors.canvasLight,
          color: colors.canvasDark,
          borderColor: colors.canvasLight,
        }}
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
        style={{ flex: 1, minWidth: 100, accentColor: colors.primary }}
      />
      <span
        style={{
          fontSize: 13,
          color: colors.stone,
          fontVariantNumeric: "tabular-nums",
          minWidth: 64,
        }}
      >
        {frameIdx + 1} / {totalFrames}
      </span>

      {/* Speed selector */}
      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
        <span style={{ fontSize: 13, color: colors.stone }}>Speed:</span>
        {SPEEDS.map((s) => (
          <button
            key={s}
            onClick={() => onSpeedChange(s)}
            style={{
              ...pill,
              padding: "6px 12px",
              background: speed === s ? colors.surfaceElevated : "transparent",
              color: speed === s ? colors.onDark : colors.stone,
              borderColor: speed === s ? colors.hairlineDark : "transparent",
            }}
          >
            {s}×
          </button>
        ))}
      </div>
    </div>
  );
}
