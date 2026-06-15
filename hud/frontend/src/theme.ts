// Design tokens extracted from design.md (Revolut-style two-mode canvas).
// True-black storytelling canvas, cobalt-violet brand accent used scarcely,
// pill buttons (rounded.full), rounded.lg cards, Inter body type.

export const colors = {
  // Surface
  canvasDark: "#000000",
  canvasLight: "#ffffff",
  surfaceDeep: "#0a0a0a",
  surfaceElevated: "#16181a",
  surfaceSoft: "#f4f4f4",
  hairlineDark: "rgba(255,255,255,0.12)",
  hairlineStrong: "#191c1f",

  // Brand
  primary: "#494fdf",
  primaryBright: "#4f55f1",
  primaryDeep: "#3a40c4",
  onPrimary: "#ffffff",

  // Text on dark
  onDark: "#ffffff",
  onDarkMute: "rgba(255,255,255,0.72)",
  stone: "#8d969e",
  faint: "#c9c9cd",

  // Semantic accents (illustrations / status only — never button surfaces)
  teal: "#00a87e",
  lightGreen: "#428619",
  yellow: "#b09000",
  warning: "#ec7e00",
  pink: "#e61e49",
  danger: "#e23b4a",
  deepRed: "#8b0000",
  blueLink: "#376cd5",
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 20,
  xl: 28,
  full: 9999,
} as const;

export const space = {
  xxs: 4,
  xs: 6,
  sm: 8,
  md: 14,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const font = {
  // Aeonik Pro substitutes per design.md; Inter for body.
  display: "'General Sans', 'Inter', system-ui, sans-serif",
  body: "'Inter', system-ui, sans-serif",
} as const;

// Status colour mapping for peers and hazards (semantic accents).
export const statusColor: Record<string, string> = {
  ok: colors.lightGreen,
  overload: colors.warning,
  distress: colors.danger,
  down: colors.deepRed,
  lost: colors.stone,
};

export const hazardColor: Record<string, string> = {
  VICTIM: colors.danger,
  ESCAPE_ROUTE: colors.lightGreen,
  FIRE_POINT: colors.warning,
  STRUCTURAL: colors.stone,
  TEAMMATE: colors.teal,
};
