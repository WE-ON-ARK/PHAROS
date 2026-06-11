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

// ── Team networking types ─────────────────────────────────────────────────────

export type PeerStatusKind = "ok" | "overload" | "distress" | "down" | "lost";

export type EventKindValue =
  | "mayday"
  | "flashover_warning"
  | "structural_collapse"
  | "new_victim"
  | "lost_contact"
  | "overload_alert"
  | "evacuate"
  | "recovered";

export interface TeamEvent {
  event_id: string;
  kind: EventKindValue;
  source_node: string;
  timestamp: number;
  position: [number, number];
  message: string;
}

export interface PeerView {
  node_id: string;
  timestamp: number;
  position: [number, number];
  cognitive_load: number;
  visibility: number;
  smoke_density: number;
  active_hazard_count: number;
  self_reported: PeerStatusKind;
  status: PeerStatusKind;
  silent_for: number;
}

export interface TeamSnapshot {
  timestamp: number;
  peers: PeerView[];
  recent_events: TeamEvent[];
}
