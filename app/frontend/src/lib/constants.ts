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
  Run:              { icon: "runner.png", label: "Run", category: "run" },
  TrailRun:         { icon: "runner.png", label: "Trail Run", category: "run" },
  VirtualRun:       { icon: "runner.png", label: "Virtual Run", category: "run" },

  // Cycling
  Ride:             { icon: "cycling.png", label: "Ride", category: "ride" },
  GravelRide:       { icon: "cycling.png", label: "Gravel Ride", category: "ride" },
  MountainBikeRide: { icon: "cycling.png", label: "Mountain Bike", category: "ride" },
  EBikeRide:        { icon: "cycling.png", label: "E-Bike Ride", category: "ride" },
  EMountainBikeRide:{ icon: "cycling.png", label: "E-MTB Ride", category: "ride" },
  VirtualRide:      { icon: "cycling.png", label: "Virtual Ride", category: "ride" },
  Velomobile:       { icon: "cycling.png", label: "Velomobile", category: "ride" },
  Handcycle:        { icon: "cycling.png", label: "Handcycle", category: "ride" },

  // Swimming
  Swim:             { icon: "default.png", label: "Swim", category: "swim" },

  // Winter sports
  AlpineSki:        { icon: "skiing.png", label: "Alpine Ski", category: "winter" },
  BackcountrySki:   { icon: "skiing.png", label: "Backcountry Ski", category: "winter" },
  NordicSki:        { icon: "skiing.png", label: "Nordic Ski", category: "winter" },
  Snowboard:        { icon: "skiing.png", label: "Snowboard", category: "winter" },
  Snowshoe:         { icon: "skiing.png", label: "Snowshoe", category: "winter" },
  IceSkate:         { icon: "skiing.png", label: "Ice Skate", category: "winter" },

  // Climbing
  RockClimbing:     { icon: "climber.png", label: "Rock Climbing", category: "climbing" },

  // Water sports
  Canoeing:         { icon: "default.png", label: "Canoeing", category: "water" },
  Kayaking:         { icon: "default.png", label: "Kayaking", category: "water" },
  Rowing:           { icon: "default.png", label: "Rowing", category: "water" },
  VirtualRow:       { icon: "default.png", label: "Virtual Row", category: "water" },
  StandUpPaddling:  { icon: "default.png", label: "SUP", category: "water" },
  Surfing:          { icon: "default.png", label: "Surfing", category: "water" },
  Kitesurf:         { icon: "default.png", label: "Kitesurf", category: "water" },
  Windsurf:         { icon: "default.png", label: "Windsurf", category: "water" },
  Sail:             { icon: "default.png", label: "Sailing", category: "water" },

  // Fitness & hiking
  Hike:             { icon: "gym.png", label: "Hike", category: "fitness" },
  Walk:             { icon: "gym.png", label: "Walk", category: "fitness" },
  Yoga:             { icon: "gym.png", label: "Yoga", category: "fitness" },
  Pilates:          { icon: "gym.png", label: "Pilates", category: "fitness" },
  WeightTraining:   { icon: "gym.png", label: "Weight Training", category: "fitness" },
  Crossfit:         { icon: "gym.png", label: "CrossFit", category: "fitness" },
  HighIntensityIntervalTraining: { icon: "gym.png", label: "HIIT", category: "fitness" },
  Elliptical:       { icon: "gym.png", label: "Elliptical", category: "fitness" },
  StairStepper:     { icon: "gym.png", label: "Stair Stepper", category: "fitness" },
  Workout:          { icon: "gym.png", label: "Workout", category: "fitness" },

  // Racquet sports & other
  Badminton:        { icon: "default.png", label: "Badminton", category: "other" },
  Golf:             { icon: "default.png", label: "Golf", category: "other" },
  InlineSkate:      { icon: "default.png", label: "Inline Skate", category: "other" },
  Pickleball:       { icon: "default.png", label: "Pickleball", category: "other" },
  Racquetball:      { icon: "default.png", label: "Racquetball", category: "other" },
  RollerSki:        { icon: "default.png", label: "Roller Ski", category: "other" },
  Skateboard:       { icon: "default.png", label: "Skateboard", category: "other" },
  Soccer:           { icon: "default.png", label: "Soccer", category: "other" },
  Squash:           { icon: "default.png", label: "Squash", category: "other" },
  TableTennis:      { icon: "default.png", label: "Table Tennis", category: "other" },
  Tennis:           { icon: "default.png", label: "Tennis", category: "other" },
  Wheelchair:       { icon: "default.png", label: "Wheelchair", category: "other" },
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
  return { icon: "default.png", label: type, category: "fitness" };
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
