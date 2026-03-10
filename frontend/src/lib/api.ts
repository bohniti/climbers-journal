// In production nginx proxies /api/* → backend; in dev set NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "/api";

// ─── Activity types ────────────────────────────────────────────────────────

export type ActivityType =
  | "bouldering"
  | "sport_climb"
  | "multi_pitch"
  | "cycling"
  | "hiking"
  | "fitness"
  | "other";

export interface Activity {
  id: number;
  created_at: string;
  updated_at: string;
  activity_type: ActivityType;
  title: string;
  date: string;
  duration_minutes?: number;
  distance_km?: number;
  elevation_gain_m?: number;
  lat?: number;
  lon?: number;
  location_name?: string;
  notes?: string;
  source: string;
  tags: string[];
  area?: string;
  partner?: string;
  intervals_activity_id?: string;
}

// ─── Session route types ───────────────────────────────────────────────────

export type GradeSystem = "yds" | "french" | "font" | "uiaa" | "ice_wis" | "alpine" | "vscale";
export type ClimbStyle = "onsight" | "flash" | "redpoint" | "top_rope" | "attempt" | "aid" | "solo";

export interface SessionRoute {
  id: number;
  activity_id: number;
  created_at: string;
  route_name?: string;
  grade?: string;
  grade_system?: GradeSystem;
  style?: ClimbStyle;
  pitches?: number;
  height_m?: number;
  rock_type?: string;
  sector?: string;
  notes?: string;
  sort_order: number;
}

export interface SessionRouteCreate {
  route_name?: string;
  grade?: string;
  grade_system?: GradeSystem;
  style?: ClimbStyle;
  pitches?: number;
  height_m?: number;
  rock_type?: string;
  sector?: string;
  notes?: string;
  sort_order?: number;
}

// ─── Chat types ────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  // Proposed data — NOT yet saved. Show to user for confirmation, then call activities.create().
  pending_activity?: Partial<Activity> & { routes?: SessionRouteCreate[] };
  needs_confirmation: boolean;
}

// ─── Stats types ───────────────────────────────────────────────────────────

export interface DayActivities {
  date: string;
  activities: Activity[];
}

export interface WeeklyStats {
  week_start: string;
  week_end: string;
  total_activities: number;
  total_hours: number;
  total_elevation_m: number;
  by_type: Record<string, number>;
  by_day: DayActivities[];
}

// ─── Import result ─────────────────────────────────────────────────────────

export interface ImportResult {
  total_fetched: number;
  imported: number;
  skipped: number;
  errors: string[];
}

// ─── Auth types ────────────────────────────────────────────────────────────

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// ─── HTTP helper ───────────────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BACKEND}${path}`, {
    headers,
    ...init,
  });

  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/")) {
    localStorage.removeItem("auth_token");
    document.cookie = "auth_token=; path=/; max-age=0";
    window.location.href = "/login";
    throw new Error("Unauthorised");
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

// ─── API client ────────────────────────────────────────────────────────────

export const api = {
  auth: {
    login: (data: LoginRequest) =>
      request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  },

  activities: {
    list: (params?: { activity_type?: string; limit?: number }) => {
      const qs = params
        ? "?" + new URLSearchParams(
            Object.entries(params)
              .filter(([, v]) => v != null)
              .map(([k, v]) => [k, String(v)])
          ).toString()
        : "";
      return request<Activity[]>(`/activities/${qs}`);
    },
    get: (id: number) => request<Activity>(`/activities/${id}`),
    create: (data: Partial<Activity> & { routes?: SessionRouteCreate[] }) =>
      request<Activity>("/activities/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Activity>) =>
      request<Activity>(`/activities/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: number) =>
      fetch(`${BACKEND}/activities/${id}`, { method: "DELETE" }),
  },

  routes: {
    list: (activityId: number) =>
      request<SessionRoute[]>(`/activities/${activityId}/routes`),
    create: (activityId: number, data: SessionRouteCreate) =>
      request<SessionRoute>(`/activities/${activityId}/routes`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (routeId: number, data: Partial<SessionRouteCreate>) =>
      request<SessionRoute>(`/routes/${routeId}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (routeId: number) =>
      fetch(`${BACKEND}/routes/${routeId}`, { method: "DELETE" }),
  },

  stats: {
    weekly: (weekStart?: string) => {
      const qs = weekStart ? `?week_start=${weekStart}` : "";
      return request<WeeklyStats>(`/stats/weekly${qs}`);
    },
  },

  import: {
    intervals: (daysBack = 365) =>
      request<ImportResult>(`/import/intervals?days_back=${daysBack}`, {
        method: "POST",
      }),
  },

  chat: (messages: ChatMessage[], location_context?: string) =>
    request<ChatResponse>("/chat/", {
      method: "POST",
      body: JSON.stringify({ messages, location_context }),
    }),
};

// ─── UI helpers ────────────────────────────────────────────────────────────

export const ACTIVITY_TYPE_LABELS: Record<ActivityType, string> = {
  bouldering: "Bouldering",
  sport_climb: "Sport Climbing",
  multi_pitch: "Multi-Pitch",
  cycling: "Cycling",
  hiking: "Hiking",
  fitness: "Fitness",
  other: "Other",
};

export const ACTIVITY_TYPE_COLORS: Record<ActivityType, string> = {
  bouldering: "bg-purple-100 text-purple-800",
  sport_climb: "bg-blue-100 text-blue-800",
  multi_pitch: "bg-amber-100 text-amber-800",
  cycling: "bg-green-100 text-green-800",
  hiking: "bg-teal-100 text-teal-800",
  fitness: "bg-orange-100 text-orange-800",
  other: "bg-gray-100 text-gray-700",
};

// Chart colours (hex for recharts)
export const ACTIVITY_TYPE_HEX: Record<ActivityType, string> = {
  bouldering: "#9333ea",
  sport_climb: "#3b82f6",
  multi_pitch: "#f59e0b",
  cycling: "#22c55e",
  hiking: "#14b8a6",
  fitness: "#f97316",
  other: "#9ca3af",
};

// Suggested tags per activity type
export const ACTIVITY_TYPE_TAGS: Record<ActivityType, string[]> = {
  bouldering: ["indoor", "outdoor"],
  sport_climb: ["indoor", "outdoor", "trad"],
  multi_pitch: ["bolted", "trad", "alpine"],
  cycling: ["commute", "road_bike", "gravel_bike", "mtb", "indoor"],
  hiking: ["alpine"],
  fitness: ["run", "trail_run", "swim", "gym", "yoga"],
  other: [],
};
