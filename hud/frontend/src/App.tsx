import { useCallback, useEffect, useRef, useState } from "react";
import { fetchReplay, fetchScene } from "./api";
import { Controls } from "./components/Controls";
import { EventFeed } from "./components/EventFeed";
import { MetricsPanel } from "./components/MetricsPanel";
import { PriorityList } from "./components/PriorityList";
import { SceneView, TRAIL_LENGTH } from "./components/SceneView";
import { TeamMap } from "./components/TeamMap";
import { useTeamWS } from "./hooks/useTeamWS";
import type { HazardInfo, HudFrame, Scenario } from "./types";

const BASE_INTERVAL_MS = 50; // matches dt=0.05s
const TEAM_FPS = 20;

type AppMode = "replay" | "team";

export default function App() {
  const [mode, setMode] = useState<AppMode>("replay");
  const [scenario, setScenario] = useState<Scenario>("a");
  const [frames, setFrames] = useState<HudFrame[]>([]);
  const [hazards, setHazards] = useState<HazardInfo[]>([]);
  const [frameIdx, setFrameIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Team live mode
  const teamSnap = useTeamWS(TEAM_FPS, mode === "team");

  // load scene hazard positions once
  useEffect(() => {
    fetchScene()
      .then((s) => setHazards(s.hazards))
      .catch(console.error);
  }, []);

  // load replay data when scenario changes
  useEffect(() => {
    if (mode !== "replay") return;
    setLoading(true);
    setIsPlaying(false);
    setFrameIdx(0);
    fetchReplay(scenario)
      .then((data) => {
        setFrames(data);
        setLoading(false);
      })
      .catch(console.error);
  }, [scenario, mode]);

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

  const trail: [number, number][] = frames
    .slice(Math.max(0, frameIdx - TRAIL_LENGTH + 1), frameIdx + 1)
    .map((f) => f.fixation);

  const headerStatus = mode === "team"
    ? (teamSnap ? `Team Live · t=${teamSnap.timestamp.toFixed(1)}s` : "Connecting…")
    : loading ? "Loading…" : `Scenario ${scenario.toUpperCase()} ready`;

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

        {/* Mode tabs */}
        <div style={{ display: "flex", gap: 4, marginLeft: 20 }}>
          {(["replay", "team"] as AppMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              style={{
                padding: "3px 12px",
                borderRadius: 4,
                border: "1px solid",
                borderColor: mode === m ? "#818cf8" : "#1e293b",
                background: mode === m ? "#1e1b4b" : "transparent",
                color: mode === m ? "#a5b4fc" : "#64748b",
                fontSize: 11,
                fontWeight: 600,
                cursor: "pointer",
                letterSpacing: "0.04em",
                textTransform: "uppercase",
              }}
            >
              {m === "replay" ? "Replay" : "Team Live"}
            </button>
          ))}
        </div>

        <span
          style={{
            marginLeft: "auto",
            fontSize: 12,
            color: mode === "team"
              ? (teamSnap ? "#22c55e" : "#f59e0b")
              : (loading ? "#f59e0b" : "#22c55e"),
          }}
        >
          {headerStatus}
        </span>
      </div>

      {/* ── Replay mode ── */}
      {mode === "replay" && (
        <>
          <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: 12 }}>
              <SceneView frame={currentFrame} hazards={hazards} trail={trail} />
            </div>
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
        </>
      )}

      {/* ── Team Live mode ── */}
      {mode === "team" && (
        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          {/* Map */}
          <div style={{ flex: 1, overflowY: "auto", borderRight: "1px solid #1e293b" }}>
            <TeamMap peers={teamSnap?.peers ?? []} />
          </div>

          {/* Right panel: per-peer metrics + event feed */}
          <div
            style={{
              width: 320,
              display: "flex",
              flexDirection: "column",
              overflowY: "auto",
            }}
          >
            {/* Peer status cards */}
            <div style={{ borderBottom: "1px solid #1e293b", padding: "12px 16px" }}>
              <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8 }}>Peer Status</div>
              {(teamSnap?.peers ?? []).map((pv) => (
                <div
                  key={pv.node_id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "4px 0",
                    fontSize: 12,
                    borderBottom: "1px solid #0f172a",
                  }}
                >
                  <span style={{ fontWeight: 600, color: "#e2e8f0" }}>{pv.node_id}</span>
                  <span style={{ fontSize: 11, color: "#94a3b8" }}>
                    CLI {(pv.cognitive_load * 100).toFixed(0)}% ·{" "}
                    {pv.visibility.toFixed(1)} m
                  </span>
                  <span
                    style={{
                      padding: "1px 6px",
                      borderRadius: 3,
                      fontSize: 10,
                      fontWeight: 700,
                      background:
                        pv.status === "ok" ? "#166534" :
                        pv.status === "overload" ? "#78350f" :
                        pv.status === "lost" ? "#1e293b" : "#7f1d1d",
                      color:
                        pv.status === "ok" ? "#4ade80" :
                        pv.status === "overload" ? "#fbbf24" :
                        pv.status === "lost" ? "#64748b" : "#fca5a5",
                    }}
                  >
                    {pv.status.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>

            {/* Event feed */}
            <EventFeed events={teamSnap?.recent_events ?? []} />
          </div>
        </div>
      )}
    </div>
  );
}
