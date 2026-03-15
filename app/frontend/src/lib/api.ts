const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ChatRequest {
  conversation_id?: string | null;
  message: string;
  provider?: string | null;
}

// ── Draft Card Types ───────────────────────────────────────────────

export interface DraftCragInfo {
  name: string;
  country: string | null;
  venue_type: string;
  status: "existing" | "new";
  grade_system: string;
}

export interface DraftAscent {
  route_name?: string;
  grade?: string | null;
  tick_type: string;
  tries?: number | null;
  notes?: string | null;
  style?: string;
  route_status?: "existing" | "new";
  route_id?: number;
}

export interface DraftCard {
  type: "climbing_session";
  crag: DraftCragInfo;
  date: string | null;
  ascents: DraftAscent[];
}

// ── Chat ───────────────────────────────────────────────────────────

export interface ChatResponse {
  conversation_id: string;
  reply: string;
  provider: string;
  draft_card: DraftCard | null;
}

export async function sendMessage(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Chat request failed (${res.status}): ${text}`);
  }

  return res.json();
}

// ── Climbing Session ───────────────────────────────────────────────

export interface ClimbingSessionRequest {
  crag_name: string;
  crag_country?: string | null;
  crag_region?: string | null;
  venue_type?: string;
  default_grade_sys?: string | null;
  ascents: {
    route_name?: string | null;
    grade?: string | null;
    tick_type: string;
    date: string;
    tries?: number | null;
    rating?: number | null;
    notes?: string | null;
    partner?: string | null;
    style?: string | null;
  }[];
}

export interface ClimbingSessionResponse {
  crag_id: number;
  crag_name: string;
  crag_created: boolean;
  ascents_created: number;
  ascents_skipped: number;
}

export async function createClimbingSession(
  req: ClimbingSessionRequest
): Promise<ClimbingSessionResponse> {
  const res = await fetch(`${API_BASE}/sessions/climbing`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to save session (${res.status}): ${text}`);
  }

  return res.json();
}

// ── Crags ─────────────────────────────────────────────────────────────

export interface CragResponse {
  id: number;
  name: string;
  country: string | null;
  region: string | null;
  venue_type: string;
  default_grade_sys: string;
}

export async function listCrags(
  opts: { offset?: number; limit?: number } = {}
): Promise<CragResponse[]> {
  const params = new URLSearchParams();
  if (opts.offset != null) params.set("offset", String(opts.offset));
  if (opts.limit != null) params.set("limit", String(opts.limit));

  const res = await fetch(`${API_BASE}/crags?${params}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch crags (${res.status}): ${text}`);
  }
  return res.json();
}

// ── Ascents ───────────────────────────────────────────────────────────

export interface AscentResponse {
  id: number;
  date: string;
  tick_type: string;
  tries: number | null;
  rating: number | null;
  notes: string | null;
  partner: string | null;
  route_id: number | null;
  crag_id: number;
  crag_name: string;
  route_name: string | null;
  grade: string | null;
}

export interface AscentFilters {
  crag_id?: number;
  tick_type?: string;
  date_from?: string;
  date_to?: string;
  offset?: number;
  limit?: number;
}

export async function listAscents(
  filters: AscentFilters = {}
): Promise<AscentResponse[]> {
  const params = new URLSearchParams();
  if (filters.crag_id != null) params.set("crag_id", String(filters.crag_id));
  if (filters.tick_type) params.set("tick_type", filters.tick_type);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (filters.offset != null) params.set("offset", String(filters.offset));
  if (filters.limit != null) params.set("limit", String(filters.limit));

  const res = await fetch(`${API_BASE}/ascents?${params}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch ascents (${res.status}): ${text}`);
  }
  return res.json();
}

// ── Dashboard / Stats ─────────────────────────────────────────────────

export interface GradePyramidEntry {
  grade: string;
  onsight: number;
  flash: number;
  redpoint: number;
  pinkpoint: number;
  repeat: number;
  total: number;
}

export interface HardestSend {
  route_name: string | null;
  grade: string;
  tick_type: string;
  crag_name: string | null;
  date: string;
}

export interface ClimbingStatsData {
  total_sends_week: number;
  total_sends_month: number;
  hardest_send: HardestSend | null;
}

export interface EnduranceStatsData {
  activities_week: number;
  total_duration_min_week: number;
  total_distance_km_week: number;
  total_training_load_week: number;
}

export interface RecentClimbingItem {
  id: number;
  date: string;
  route_name: string | null;
  grade: string | null;
  tick_type: string;
  crag_name: string | null;
}

export interface RecentEnduranceItem {
  id: number;
  date: string;
  type: string;
  name: string | null;
  duration_s: number;
  distance_m: number | null;
  training_load: number | null;
}

export interface DashboardData {
  grade_pyramid: GradePyramidEntry[];
  climbing_stats: ClimbingStatsData;
  endurance_stats: EnduranceStatsData;
  recent_climbing: RecentClimbingItem[];
  recent_endurance: RecentEnduranceItem[];
}

export async function fetchDashboard(): Promise<DashboardData> {
  const res = await fetch(`${API_BASE}/stats/dashboard`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch dashboard (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchGradePyramid(
  opts: { venue_type?: string; period?: string } = {}
): Promise<GradePyramidEntry[]> {
  const params = new URLSearchParams();
  if (opts.venue_type) params.set("venue_type", opts.venue_type);
  if (opts.period) params.set("period", opts.period);

  const res = await fetch(`${API_BASE}/stats/grade-pyramid?${params}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch grade pyramid (${res.status}): ${text}`);
  }
  return res.json();
}

// ── Calendar ─────────────────────────────────────────────────────────

export interface CalendarClimbingDay {
  route_count: number;
  hardest_grade: string | null;
  venue_type: string; // "outdoor_crag" | "indoor_gym" | "mixed"
}

export interface CalendarEnduranceDay {
  activities: { type: string; duration_s: number }[];
}

export interface CalendarDayEntry {
  date: string;
  climbing: CalendarClimbingDay | null;
  endurance: CalendarEnduranceDay | null;
}

export interface CalendarData {
  month: string;
  days: CalendarDayEntry[];
}

export async function fetchCalendar(month: string): Promise<CalendarData> {
  const res = await fetch(`${API_BASE}/stats/calendar?month=${month}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch calendar (${res.status}): ${text}`);
  }
  return res.json();
}

// ── Activities (Endurance) ────────────────────────────────────────────

export interface ActivityResponse {
  id: number;
  intervals_id: string;
  date: string;
  type: string;
  name: string | null;
  duration_s: number;
  distance_m: number | null;
  elevation_gain_m: number | null;
  avg_hr: number | null;
  max_hr: number | null;
  training_load: number | null;
  intensity: number | null;
  source: string;
}

export interface ActivityFilters {
  activity_type?: string;
  date_from?: string;
  date_to?: string;
  offset?: number;
  limit?: number;
}

export async function listActivities(
  filters: ActivityFilters = {}
): Promise<ActivityResponse[]> {
  const params = new URLSearchParams();
  if (filters.activity_type) params.set("activity_type", filters.activity_type);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (filters.offset != null) params.set("offset", String(filters.offset));
  if (filters.limit != null) params.set("limit", String(filters.limit));

  const res = await fetch(`${API_BASE}/activities?${params}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Failed to fetch activities (${res.status}): ${text}`);
  }
  return res.json();
}
