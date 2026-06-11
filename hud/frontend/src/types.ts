export interface ActiveHazard {
  id: string;
  kind: string;
  priority: number;
}

export interface HudFrame {
  timestamp: number;
  active_hazards: ActiveHazard[];
  ranked_scores: [number, string][];
  cognitive_load: number;
  smoke_density: number;
  visibility: number;
  gaze_entropy_hs: number;
  gaze_entropy_ht: number;
  fixation: [number, number];
}

export interface HazardInfo {
  id: string;
  kind: string;
  priority: number;
  position: [number, number];
}

export interface SceneInfo {
  screen_size: [number, number];
  smoke_density: number;
  hazards: HazardInfo[];
}

export type Scenario = "a" | "b";
