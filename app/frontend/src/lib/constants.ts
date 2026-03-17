// ── Tick type colors (dark-only theme) ──────────────────────────────

export const TICK_COLORS: Record<string, string> = {
  onsight: "bg-amber-900/40 text-amber-300",
  flash: "bg-yellow-900/40 text-yellow-300",
  redpoint: "bg-red-900/40 text-red-300",
  pinkpoint: "bg-pink-900/40 text-pink-300",
  repeat: "bg-green-900/40 text-green-300",
  attempt: "bg-slate-800 text-slate-400",
  hang: "bg-slate-800 text-slate-400",
};

// ── Grade pyramid bar colors (dark-only) ────────────────────────────

export const PYRAMID_COLORS: Record<string, string> = {
  onsight: "bg-amber-400",
  flash: "bg-yellow-400",
  redpoint: "bg-red-400",
  pinkpoint: "bg-pink-400",
  repeat: "bg-green-400",
};

// ── Strava-aligned sport type taxonomy ──────────────────────────────

export type SportCategory =
  | "run"
  | "ride"
  | "swim"
  | "winter"
  | "climbing"
  | "water"
  | "fitness"
  | "other";

export interface SportTypeInfo {
  icon: string;
  label: string;
  category: SportCategory;
}

export const SPORT_TYPES: Record<string, SportTypeInfo> = {
  // Running
  Run:              { icon: "🏃", label: "Run", category: "run" },
  TrailRun:         { icon: "⛰️", label: "Trail Run", category: "run" },
  VirtualRun:       { icon: "🏃", label: "Virtual Run", category: "run" },

  // Cycling
  Ride:             { icon: "🚴", label: "Ride", category: "ride" },
  GravelRide:       { icon: "🚴", label: "Gravel Ride", category: "ride" },
  MountainBikeRide: { icon: "🚵", label: "Mountain Bike", category: "ride" },
  EBikeRide:        { icon: "🚴", label: "E-Bike Ride", category: "ride" },
  EMountainBikeRide:{ icon: "🚵", label: "E-MTB Ride", category: "ride" },
  VirtualRide:      { icon: "🚴", label: "Virtual Ride", category: "ride" },
  Velomobile:       { icon: "🚴", label: "Velomobile", category: "ride" },
  Handcycle:        { icon: "🚴", label: "Handcycle", category: "ride" },

  // Swimming
  Swim:             { icon: "🏊", label: "Swim", category: "swim" },

  // Winter sports
  AlpineSki:        { icon: "⛷️", label: "Alpine Ski", category: "winter" },
  BackcountrySki:   { icon: "🎿", label: "Backcountry Ski", category: "winter" },
  NordicSki:        { icon: "🎿", label: "Nordic Ski", category: "winter" },
  Snowboard:        { icon: "🏂", label: "Snowboard", category: "winter" },
  Snowshoe:         { icon: "🥾", label: "Snowshoe", category: "winter" },
  IceSkate:         { icon: "⛸️", label: "Ice Skate", category: "winter" },

  // Climbing
  RockClimbing:     { icon: "🧗", label: "Rock Climbing", category: "climbing" },

  // Water sports
  Canoeing:         { icon: "🛶", label: "Canoeing", category: "water" },
  Kayaking:         { icon: "🛶", label: "Kayaking", category: "water" },
  Rowing:           { icon: "🚣", label: "Rowing", category: "water" },
  VirtualRow:       { icon: "🚣", label: "Virtual Row", category: "water" },
  StandUpPaddling:  { icon: "🏄", label: "SUP", category: "water" },
  Surfing:          { icon: "🏄", label: "Surfing", category: "water" },
  Kitesurf:         { icon: "🪁", label: "Kitesurf", category: "water" },
  Windsurf:         { icon: "🏄", label: "Windsurf", category: "water" },
  Sail:             { icon: "⛵", label: "Sailing", category: "water" },

  // Fitness & hiking
  Hike:             { icon: "🥾", label: "Hike", category: "fitness" },
  Walk:             { icon: "🚶", label: "Walk", category: "fitness" },
  Yoga:             { icon: "🧘", label: "Yoga", category: "fitness" },
  Pilates:          { icon: "🧘", label: "Pilates", category: "fitness" },
  WeightTraining:   { icon: "🏋️", label: "Weight Training", category: "fitness" },
  Crossfit:         { icon: "🏋️", label: "CrossFit", category: "fitness" },
  HighIntensityIntervalTraining: { icon: "🔥", label: "HIIT", category: "fitness" },
  Elliptical:       { icon: "🏋️", label: "Elliptical", category: "fitness" },
  StairStepper:     { icon: "🏋️", label: "Stair Stepper", category: "fitness" },
  Workout:          { icon: "💪", label: "Workout", category: "fitness" },

  // Racquet sports & other
  Badminton:        { icon: "🏸", label: "Badminton", category: "other" },
  Golf:             { icon: "⛳", label: "Golf", category: "other" },
  InlineSkate:      { icon: "🛼", label: "Inline Skate", category: "other" },
  Pickleball:       { icon: "🏓", label: "Pickleball", category: "other" },
  Racquetball:      { icon: "🏸", label: "Racquetball", category: "other" },
  RollerSki:        { icon: "🎿", label: "Roller Ski", category: "other" },
  Skateboard:       { icon: "🛹", label: "Skateboard", category: "other" },
  Soccer:           { icon: "⚽", label: "Soccer", category: "other" },
  Squash:           { icon: "🏸", label: "Squash", category: "other" },
  TableTennis:      { icon: "🏓", label: "Table Tennis", category: "other" },
  Tennis:           { icon: "🎾", label: "Tennis", category: "other" },
  Wheelchair:       { icon: "♿", label: "Wheelchair", category: "other" },
};

// ── Climbing sub-type icons ─────────────────────────────────────────

export const CLIMBING_STYLE_ICONS: Record<string, string> = {
  sport:      "🧗",
  boulder:    "🪨",
  multi_pitch:"⛰️",
  trad:       "🏔️",
  alpine:     "🏔️",
};

// ── Category chart colors (hex for Recharts + badge) ────────────────

export const CATEGORY_COLORS: Record<SportCategory, { hex: string; badge: string; label: string }> = {
  climbing: { hex: "#ef4444", badge: "bg-red-900/40 text-red-300", label: "Climbing" },
  run:      { hex: "#3b82f6", badge: "bg-blue-900/40 text-blue-300", label: "Run" },
  ride:     { hex: "#22c55e", badge: "bg-green-900/40 text-green-300", label: "Ride" },
  swim:     { hex: "#06b6d4", badge: "bg-cyan-900/40 text-cyan-300", label: "Swim" },
  winter:   { hex: "#8b5cf6", badge: "bg-violet-900/40 text-violet-300", label: "Winter" },
  water:    { hex: "#0ea5e9", badge: "bg-sky-900/40 text-sky-300", label: "Water" },
  fitness:  { hex: "#f97316", badge: "bg-orange-900/40 text-orange-300", label: "Fitness" },
  other:    { hex: "#9ca3af", badge: "bg-slate-800 text-slate-400", label: "Other" },
};

// ── Venue colors (dark-only) ────────────────────────────────────────

export const VENUE_COLORS: Record<string, string> = {
  outdoor_crag: "text-red-400",
  indoor_gym: "text-violet-400",
  mixed: "text-orange-400",
};

// ── Helpers ─────────────────────────────────────────────────────────

export function tickTypeLabel(tt: string): string {
  return tt.charAt(0).toUpperCase() + tt.slice(1);
}

/** Get sport type info for a Strava/intervals.icu type string */
export function getSportType(type: string): SportTypeInfo {
  if (SPORT_TYPES[type]) return SPORT_TYPES[type];
  // Unknown type — fallback to Workout with warning
  if (typeof window !== "undefined") {
    console.warn(`Unknown sport type: "${type}", falling back to Workout`);
  }
  return { icon: "💪", label: type, category: "fitness" };
}

/** Get the icon for a sport type */
export function sportIcon(type: string): string {
  return getSportType(type).icon;
}

/** Map a sport type string to its category */
export function sportCategory(type: string): SportCategory {
  return getSportType(type).category;
}

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function formatDistance(meters: number): string {
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
  return `${Math.round(meters)} m`;
}
