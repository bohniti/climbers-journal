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

// ── Activity icons (emoji) ──────────────────────────────────────────

export const ACTIVITY_ICONS: Record<string, string> = {
  Run: "\u{1F3C3}",
  Ride: "\u{1F6B4}",
  Hike: "\u{1F6B6}",
  TrailRun: "\u{26F0}",
  Swim: "\u{1F3CA}",
  Walk: "\u{1F6B6}",
  VirtualRide: "\u{1F6B4}",
};

// ── Activity type chart colors (hex for Recharts) ───────────────────

export const ACTIVITY_TYPE_COLORS: Record<string, { hex: string; badge: string }> = {
  bouldering: { hex: "#9333ea", badge: "bg-purple-900/40 text-purple-300" },
  sport_climb: { hex: "#3b82f6", badge: "bg-blue-900/40 text-blue-300" },
  multi_pitch: { hex: "#f59e0b", badge: "bg-amber-900/40 text-amber-300" },
  cycling: { hex: "#22c55e", badge: "bg-green-900/40 text-green-300" },
  hiking: { hex: "#14b8a6", badge: "bg-teal-900/40 text-teal-300" },
  fitness: { hex: "#f97316", badge: "bg-orange-900/40 text-orange-300" },
  other: { hex: "#9ca3af", badge: "bg-slate-800 text-slate-400" },
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

export function activityIcon(type: string): string {
  return ACTIVITY_ICONS[type] ?? "\u{1F4AA}";
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
