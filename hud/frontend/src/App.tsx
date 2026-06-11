import { useCallback, useEffect, useRef, useState } from "react";
import { fetchReplay, fetchScene } from "./api";
import { Controls } from "./components/Controls";
import { MetricsPanel } from "./components/MetricsPanel";
import { PriorityList } from "./components/PriorityList";
import { SceneView, TRAIL_LENGTH } from "./components/SceneView";
import type { HazardInfo, HudFrame, Scenario } from "./types";

const BASE_INTERVAL_MS = 50; // matches dt=0.05s

export default function App() {
  const [scenario, setScenario] = useState<Scenario>("a");
  const [frames, setFrames] = useState<HudFrame[]>([]);
  const [hazards, setHazards] = useState<HazardInfo[]>([]);
  const [frameIdx, setFrameIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // load scene hazard positions once
  useEffect(() => {
    fetchScene()
      .then((s) => setHazards(s.hazards))
      .catch(console.error);
  }, []);

  // load replay data when scenario changes
  useEffect(() => {
    setLoading(true);
    setIsPlaying(false);
    setFrameIdx(0);
    fetchReplay(scenario)
      .then((data) => {
        setFrames(data);
        setLoading(false);
      })
      .catch(console.error);
  }, [scenario]);

  // playback loop
  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (!isPlaying || frames.length === 0) return;
    const interval = BASE_INTERVAL_MS / speed;
    timerRef.current = setInterval(() => {
      setFrameIdx((prev) => {
        if (prev >= frames.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, interval);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, speed, frames.length]);

  const handleScenarioChange = useCallback((s: Scenario) => {
    setScenario(s);
  }, []);

  const handleRestart = useCallback(() => {
    setFrameIdx(0);
    setIsPlaying(false);
  }, []);

  const currentFrame = frames[frameIdx] ?? null;

  // build gaze trail from recent frames
  const trail: [number, number][] = frames
    .slice(Math.max(0, frameIdx - TRAIL_LENGTH + 1), frameIdx + 1)
    .map((f) => f.fixation);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "#0f172a",
        color: "#f1f5f9",
        fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "8px 20px",
          background: "#020617",
          borderBottom: "1px solid #1e293b",
          gap: 12,
        }}
      >
        <span style={{ fontWeight: 700, fontSize: 16, letterSpacing: "0.08em", color: "#818cf8" }}>
          PHAROS
        </span>
        <span style={{ fontSize: 11, color: "#475569" }}>
          Priority · Hazard · Attention · Reorganizing · Overload · Suppression
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontSize: 12,
            color: loading ? "#f59e0b" : "#22c55e",
          }}
        >
          {loading ? "Loading…" : `Scenario ${scenario.toUpperCase()} ready`}
        </span>
      </div>

      {/* Main layout */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Scene canvas */}
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 12 }}>
          <SceneView frame={currentFrame} hazards={hazards} trail={trail} />
        </div>

        {/* Right panel */}
        <div
          style={{
            width: 260,
            display: "flex",
            flexDirection: "column",
            borderLeft: "1px solid #1e293b",
            overflowY: "auto",
          }}
        >
          <div style={{ borderBottom: "1px solid #1e293b" }}>
            <MetricsPanel frame={currentFrame} />
          </div>
          <PriorityList frame={currentFrame} />
        </div>
      </div>

      {/* Controls */}
      <Controls
        scenario={scenario}
        onScenarioChange={handleScenarioChange}
        isPlaying={isPlaying}
        onPlayPause={() => setIsPlaying((p) => !p)}
        onRestart={handleRestart}
        frameIdx={frameIdx}
        totalFrames={frames.length}
        onSeek={setFrameIdx}
        speed={speed}
        onSpeedChange={setSpeed}
      />
    </div>
  );
}
