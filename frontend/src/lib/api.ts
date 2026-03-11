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
  region?: string;
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
  tries?: number;    // attempts before send (1 = onsight/flash, 2+ = multiple goes)
  stars?: number;    // personal rating 0–3
  url?: string;      // link to route on thecrag / bergsteigen / mountain project
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
  tries?: number;
  stars?: number;
  url?: string;
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

export interface BlogCsvImportResult {
  imported_sessions: number;
  imported_routes: number;
  skipped_sessions: number;
  errors: string[];
}

// ─── Photo types ──────────────────────────────────────────────────────

export interface ActivityPhoto {
  id: number;
  activity_id: number;
  filename: string;
  original_name: string;
  content_type: string;
  size_bytes: number;
  exif_lat?: number;
  exif_lon?: number;
  exif_date?: string;
  created_at: string;
}

// ─── Refine types ─────────────────────────────────────────────────────

export interface RefineSuggestion {
  field: string;
  current_value: unknown;
  suggested_value: unknown;
}

export interface RefineResponse {
  suggestions: RefineSuggestion[];
  explanation: string;
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

function getTokenFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)auth_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("auth_token");
  document.cookie = "auth_token=; path=/; max-age=0";
  window.location.href = "/login";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // Read token from localStorage, fall back to cookie if localStorage was cleared
  const token =
    typeof window !== "undefined"
      ? (localStorage.getItem("auth_token") || getTokenFromCookie())
      : null;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BACKEND}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
  });

  // 401 = expired/invalid token, 403 = missing token (FastAPI HTTPBearer behaviour)
  if ((res.status === 401 || res.status === 403) && !path.startsWith("/auth/")) {
    redirectToLogin();
    throw new Error("Session expired — please log in again.");
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
    list: (params?: { activity_type?: string; region?: string; limit?: number; offset?: number }) => {
      const qs = params
        ? "?" + new URLSearchParams(
            Object.entries(params)
              .filter(([, v]) => v != null)
              .map(([k, v]) => [k, String(v)])
          ).toString()
        : "";
      return request<Activity[]>(`/activities/${qs}`);
    },
    regions: () => request<string[]>("/activities/regions"),
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
    blogCsv: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const token =
        typeof window !== "undefined"
          ? (localStorage.getItem("auth_token") || null)
          : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      return fetch(`${BACKEND}/import/blog-csv`, {
        method: "POST",
        headers,
        body: form,
      }).then((r) => r.json() as Promise<BlogCsvImportResult>);
    },
  },

  photos: {
    list: (activityId: number) =>
      request<ActivityPhoto[]>(`/activities/${activityId}/photos`),

    upload: (activityId: number, files: FileList | File[]) => {
      const form = new FormData();
      Array.from(files).forEach((f) => form.append("files", f));
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("auth_token") || null
          : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      return fetch(`${BACKEND}/activities/${activityId}/photos`, {
        method: "POST",
        headers,
        body: form,
      }).then((r) => {
        if (!r.ok) throw new Error(`Upload failed: ${r.status}`);
        return r.json() as Promise<ActivityPhoto[]>;
      });
    },

    fileUrl: (photoId: number) => `${BACKEND}/photos/${photoId}/file`,

    delete: (photoId: number) => {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("auth_token") || null
          : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      return fetch(`${BACKEND}/photos/${photoId}`, {
        method: "DELETE",
        headers,
      });
    },
  },

  refine: {
    suggest: (activityId: number) =>
      request<RefineResponse>(`/activities/${activityId}/refine`, {
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
