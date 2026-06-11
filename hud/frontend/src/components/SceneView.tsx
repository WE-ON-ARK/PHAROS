import { useEffect, useRef } from "react";
import type { HazardInfo, HudFrame } from "../types";

const KIND_COLOR: Record<string, string> = {
  VICTIM: "#ef4444",
  ESCAPE_ROUTE: "#22c55e",
  FIRE_POINT: "#f97316",
  STRUCTURAL: "#94a3b8",
  TEAMMATE: "#3b82f6",
};

const TRAIL_LENGTH = 20;

interface Props {
  frame: HudFrame | null;
  hazards: HazardInfo[];
  trail: [number, number][];
}

export function SceneView({ frame, hazards, trail }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // background — dark smoke-tinted fill
    const smokeDensity = frame?.smoke_density ?? 0;
    const bg = Math.round(20 + smokeDensity * 30);
    ctx.fillStyle = `rgb(${bg},${bg},${bg})`;
    ctx.fillRect(0, 0, 800, 600);

    // gaze trail
    for (let i = 0; i < trail.length; i++) {
      const alpha = ((i + 1) / trail.length) * 0.55;
      ctx.beginPath();
      ctx.arc(trail[i][0], trail[i][1], 5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(250,250,100,${alpha})`;
      ctx.fill();
    }

    // current fixation crosshair
    if (frame) {
      const [fx, fy] = frame.fixation;
      ctx.strokeStyle = "rgba(250,250,100,0.9)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(fx - 12, fy);
      ctx.lineTo(fx + 12, fy);
      ctx.moveTo(fx, fy - 12);
      ctx.lineTo(fx, fy + 12);
      ctx.stroke();
    }

    // hazard markers
    const activeIds = new Set(frame?.active_hazards.map((h) => h.id) ?? []);
    for (const h of hazards) {
      const [hx, hy] = h.position;
      const color = KIND_COLOR[h.kind] ?? "#fff";
      const isActive = activeIds.has(h.id);

      if (isActive) {
        ctx.shadowColor = color;
        ctx.shadowBlur = 18;
      } else {
        ctx.shadowBlur = 0;
      }

      ctx.beginPath();
      ctx.arc(hx, hy, isActive ? 18 : 12, 0, Math.PI * 2);
      ctx.fillStyle = color + (isActive ? "dd" : "66");
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = isActive ? 2.5 : 1;
      ctx.stroke();

      ctx.shadowBlur = 0;
      ctx.fillStyle = "#fff";
      ctx.font = isActive ? "bold 11px monospace" : "10px monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(h.id.toUpperCase().slice(0, 3), hx, hy);
    }
  }, [frame, hazards, trail]);

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={600}
      style={{ display: "block", width: "100%", borderRadius: 4 }}
    />
  );
}

export { TRAIL_LENGTH };
