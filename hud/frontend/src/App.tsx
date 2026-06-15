import { useCallback, useEffect, useRef, useState } from "react";
import { fetchReplay, fetchScene } from "./api";
import { CameraView } from "./components/CameraView";
import { Controls } from "./components/Controls";
import { EventFeed } from "./components/EventFeed";
import { MetricsPanel } from "./components/MetricsPanel";
import { PriorityList } from "./components/PriorityList";
import { SceneView, TRAIL_LENGTH } from "./components/SceneView";
import { TeamMap } from "./components/TeamMap";
import { useCameraWS } from "./hooks/useCameraWS";
import { useTeamWS } from "./hooks/useTeamWS";
import { colors, font, radius, statusColor } from "./theme";
import type { HazardInfo, HudFrame, Scenario } from "./types";

const BASE_INTERVAL_MS = 50; // matches dt=0.05s
const TEAM_FPS = 20;
const CAMERA_FPS = 15;

type AppMode = "replay" | "team" | "camera";

const MODE_LABEL: Record<AppMode, string> = {
  replay: "Replay",
  team: "Team Live",
  camera: "Live Camera",
};

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

  const teamSnap = useTeamWS(TEAM_FPS, mode === "team");
  const { message: cameraMsg, error: cameraErr } = useCameraWS(
    CAMERA_FPS,
    mode === "camera"
  );

  useEffect(() => {
    fetchScene()
      .then((s) => setHazards(s.hazards))
      .catch(console.error);
  }, []);

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

  const handleScenarioChange = useCallback((s: Scenario) => setScenario(s), []);
  const handleRestart = useCallback(() => {
    setFrameIdx(0);
    setIsPlaying(false);
  }, []);

  const currentFrame = frames[frameIdx] ?? null;
  const trail: [number, number][] = frames
    .slice(Math.max(0, frameIdx - TRAIL_LENGTH + 1), frameIdx + 1)
    .map((f) => f.fixation);

  const headerStatus =
    mode === "team"
      ? teamSnap
        ? `Team Live · t=${teamSnap.timestamp.toFixed(1)}s`
        : "Connecting…"
      : mode === "camera"
        ? cameraErr
          ? "Camera offline"
          : cameraMsg
            ? "Live Camera · streaming"
            : "Connecting…"
        : loading
          ? "Loading…"
          : `Scenario ${scenario.toUpperCase()} ready`;

  const statusOk =
    mode === "team"
      ? Boolean(teamSnap)
      : mode === "camera"
        ? Boolean(cameraMsg) && !cameraErr
        : !loading;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: colors.canvasDark,
        color: colors.onDark,
        fontFamily: font.body,
        overflow: "hidden",
      }}
    >
      {/* ── Header ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "16px 24px",
          background: colors.canvasDark,
          borderBottom: `1px solid ${colors.hairlineDark}`,
          gap: 16,
        }}
      >
        <span
          style={{
            fontFamily: font.display,
            fontWeight: 600,
            fontSize: 26,
            letterSpacing: "-0.01em",
            color: colors.onDark,
          }}
        >
          PHAROS
        </span>
        <span style={{ fontSize: 12, color: colors.stone, maxWidth: 280, lineHeight: 1.4 }}>
          Priority · Hazard · Attention · Reorganizing · Overload · Suppression
        </span>

        {/* Mode tabs — pill nav */}
        <div style={{ display: "flex", gap: 8, marginLeft: 24 }}>
          {(["replay", "team", "camera"] as AppMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              style={{
                padding: "8px 18px",
                borderRadius: radius.full,
                border: `1px solid ${mode === m ? colors.primary : colors.hairlineDark}`,
                background: mode === m ? colors.primary : "transparent",
                color: mode === m ? colors.onPrimary : colors.onDarkMute,
                fontSize: 14,
                fontWeight: 600,
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              {MODE_LABEL[m]}
            </button>
          ))}
        </div>

        <span
          style={{
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 14,
            color: colors.onDarkMute,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: radius.full,
              background: statusOk ? colors.lightGreen : colors.warning,
            }}
          />
          {headerStatus}
        </span>
      </div>

      {/* ── Replay mode ── */}
      {mode === "replay" && (
        <>
          <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 24,
              }}
            >
              <SceneView frame={currentFrame} hazards={hazards} trail={trail} />
            </div>
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
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              borderRight: `1px solid ${colors.hairlineDark}`,
            }}
          >
            <TeamMap peers={teamSnap?.peers ?? []} />
          </div>
          <div
            style={{
              width: 320,
              display: "flex",
              flexDirection: "column",
              overflowY: "auto",
            }}
          >
            <div
              style={{
                borderBottom: `1px solid ${colors.hairlineDark}`,
                padding: "16px 20px",
              }}
            >
              <div
                style={{
                  fontSize: 12,
                  color: colors.stone,
                  marginBottom: 12,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                Peer Status
              </div>
              {(teamSnap?.peers ?? []).map((pv) => (
                <div
                  key={pv.node_id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 0",
                    fontSize: 14,
                    borderBottom: `1px solid ${colors.hairlineDark}`,
                  }}
                >
                  <span style={{ fontWeight: 600, color: colors.onDark }}>
                    {pv.node_id}
                  </span>
                  <span style={{ fontSize: 13, color: colors.onDarkMute }}>
                    CLI {(pv.cognitive_load * 100).toFixed(0)}% ·{" "}
                    {pv.visibility.toFixed(1)} m
                  </span>
                  <span
                    style={{
                      padding: "3px 10px",
                      borderRadius: radius.full,
                      fontSize: 11,
                      fontWeight: 700,
                      background: statusColor[pv.status] ?? colors.stone,
                      color: colors.onPrimary,
                    }}
                  >
                    {pv.status.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
            <EventFeed events={teamSnap?.recent_events ?? []} />
          </div>
        </div>
      )}

      {/* ── Live Camera mode ── */}
      {mode === "camera" && <CameraView message={cameraMsg} error={cameraErr} />}
    </div>
  );
}
