import type { HudFrame, SceneInfo, Scenario } from "./types";

export async function fetchReplay(scenario: Scenario): Promise<HudFrame[]> {
  const res = await fetch(`/api/replay/${scenario}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<HudFrame[]>;
}

export async function fetchScene(): Promise<SceneInfo> {
  const res = await fetch("/api/scene");
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<SceneInfo>;
}
