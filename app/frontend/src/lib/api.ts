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
    notes?: string | null;
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
