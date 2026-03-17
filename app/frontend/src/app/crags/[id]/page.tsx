"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  fetchCrag,
  fetchCragStats,
  fetchCragSessions,
  type CragResponse,
  type CragStatsResponse,
  type CragSessionResponse,
  type FeedSessionAscent,
} from "@/lib/api";
import {
  TICK_COLORS,
  tickTypeLabel,
  formatDuration,
  formatDate,
} from "@/lib/constants";

const PAGE_SIZE = 20;

export default function CragDetailPage() {
  const params = useParams();
  const cragId = Number(params.id);

  const [crag, setCrag] = useState<CragResponse | null>(null);
  const [stats, setStats] = useState<CragStatsResponse | null>(null);
  const [sessions, setSessions] = useState<CragSessionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionOffset, setSessionOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(false);

  useEffect(() => {
    if (!cragId) return;
    setLoading(true);
    setError(null);

    Promise.all([fetchCrag(cragId), fetchCragStats(cragId)])
      .then(([cragData, statsData]) => {
        setCrag(cragData);
        setStats(statsData);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load crag");
      })
      .finally(() => setLoading(false));
  }, [cragId]);

  const loadSessions = useCallback(
    async (offset: number, append: boolean) => {
      if (!cragId) return;
      setLoadingSessions(true);
      try {
        const data = await fetchCragSessions(cragId, {
          offset,
          limit: PAGE_SIZE,
        });
        setHasMore(data.length === PAGE_SIZE);
        setSessionOffset(offset + data.length);
        if (append) {
          setSessions((prev) => [...prev, ...data]);
        } else {
          setSessions(data);
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load sessions"
        );
      } finally {
        setLoadingSessions(false);
      }
    },
    [cragId]
  );

  useEffect(() => {
    if (cragId) loadSessions(0, false);
  }, [cragId, loadSessions]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-400">
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="rounded-lg border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      </div>
    );
  }

  if (!crag || !stats) return null;

  const venueLabel =
    crag.venue_type === "indoor_gym" ? "Indoor gym" : "Outdoor crag";

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <div className="mx-auto w-full max-w-3xl px-4 py-6">
        {/* Breadcrumb */}
        <div className="mb-4 text-xs text-slate-500">
          <Link href="/crags" className="hover:text-slate-300">
            Crags
          </Link>
          <span className="mx-1.5">/</span>
          <span className="text-slate-300">{crag.name}</span>
        </div>

        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-slate-100">
              {crag.name}
            </h1>
            <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
              {venueLabel}
            </span>
          </div>
          {(crag.country || crag.region) && (
            <p className="mt-1 text-sm text-slate-400">
              {[crag.region, crag.country].filter(Boolean).join(", ")}
            </p>
          )}
        </div>

        {/* Stats bar */}
        <div className="mb-6 flex flex-wrap gap-4 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3">
          <StatItem
            label="Sessions"
            value={String(stats.session_count)}
          />
          <StatItem
            label="Routes logged"
            value={String(stats.ascent_count)}
          />
          {stats.hardest_send && (
            <StatItem
              label="Best send"
              value={`${stats.hardest_send.grade}${stats.hardest_send.route_name ? ` (${stats.hardest_send.route_name})` : ""}`}
            />
          )}
          {stats.last_visited && (
            <StatItem
              label="Last visited"
              value={formatDate(stats.last_visited)}
            />
          )}
        </div>

        {/* Session history */}
        <h2 className="mb-3 text-sm font-medium text-slate-300">
          Session history
        </h2>

        {sessions.length === 0 && !loadingSessions && (
          <p className="text-sm text-slate-500">No sessions yet</p>
        )}

        <div className="space-y-2">
          {sessions.map((session) => (
            <SessionCard key={session.id} session={session} />
          ))}
        </div>

        {loadingSessions && (
          <div className="py-8 text-center text-sm text-slate-400">
            Loading...
          </div>
        )}
        {!loadingSessions && hasMore && sessions.length > 0 && (
          <div className="py-6 text-center">
            <button
              onClick={() => loadSessions(sessionOffset, true)}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-800"
            >
              Load more sessions
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className="truncate text-sm font-medium text-slate-100">{value}</p>
    </div>
  );
}

// ── Session Card (reused pattern from log page) ──────────────────────

type ExpandLevel = "collapsed" | "summary" | "routes";

function SessionCard({ session }: { session: CragSessionResponse }) {
  const defaultLevel: ExpandLevel =
    session.ascent_count > 10 ? "summary" : "collapsed";
  const [expand, setExpand] = useState<ExpandLevel>(defaultLevel);

  const cycleExpand = () => {
    if (expand === "collapsed") setExpand("summary");
    else if (expand === "summary") setExpand("routes");
    else setExpand("collapsed");
  };

  const ascents = session.ascents;
  const grades = ascents
    .map((a) => a.grade)
    .filter((g): g is string => g != null)
    .sort();
  const hardestGrade = grades.length > 0 ? grades[grades.length - 1] : null;

  const sends = ascents.filter(
    (a) => a.tick_type !== "attempt" && a.tick_type !== "hang"
  );
  const attempts = ascents.filter(
    (a) => a.tick_type === "attempt" || a.tick_type === "hang"
  );

  const tickBreakdown: Record<string, number> = {};
  for (const a of ascents) {
    tickBreakdown[a.tick_type] = (tickBreakdown[a.tick_type] || 0) + 1;
  }

  const linkedDuration = session.linked_activity?.duration_s;

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 text-left transition-colors hover:border-slate-600">
      <button type="button" onClick={cycleExpand} className="w-full px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-red-900/30 text-lg">
            {"\u{1F9D7}"}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="truncate text-sm font-medium text-slate-100">
                {formatDate(session.date)}
              </span>
              {linkedDuration != null && (
                <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-400">
                  {formatDuration(linkedDuration)}
                </span>
              )}
            </div>
            <div className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-400">
              <span>
                {session.ascent_count} route
                {session.ascent_count !== 1 ? "s" : ""}
              </span>
              {hardestGrade && (
                <>
                  <span>&middot;</span>
                  <span className="font-mono">{hardestGrade}</span>
                </>
              )}
            </div>
          </div>
          <div className="hidden shrink-0 gap-1 sm:flex">
            {Object.entries(tickBreakdown).map(([tt, count]) => (
              <span
                key={tt}
                className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                  TICK_COLORS[tt] ?? TICK_COLORS.attempt
                }`}
              >
                {count}&times; {tickTypeLabel(tt)}
              </span>
            ))}
          </div>
        </div>
      </button>

      {(expand === "summary" || expand === "routes") && (
        <div className="border-t border-slate-800 px-4 py-2.5">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>
              {session.ascent_count} routes
              {hardestGrade ? ` \u00B7 hardest ${hardestGrade}` : ""}
              {` \u00B7 ${sends.length} send${sends.length !== 1 ? "s" : ""}`}
              {attempts.length > 0
                ? ` \u00B7 ${attempts.length} attempt${attempts.length !== 1 ? "s" : ""}`
                : ""}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setExpand(expand === "routes" ? "summary" : "routes");
              }}
              className="text-emerald-400 hover:text-emerald-300"
            >
              {expand === "routes"
                ? "Hide routes"
                : `Show all ${session.ascent_count} routes`}
            </button>
          </div>

          {session.linked_activity && (
            <div className="mt-1.5 flex gap-3 text-[11px] text-slate-500">
              {session.linked_activity.avg_hr != null && (
                <span>Avg HR: {session.linked_activity.avg_hr} bpm</span>
              )}
              {session.linked_activity.max_hr != null && (
                <span>Max HR: {session.linked_activity.max_hr} bpm</span>
              )}
            </div>
          )}

          {session.notes && (
            <p className="mt-1.5 text-xs text-slate-400">{session.notes}</p>
          )}
        </div>
      )}

      {expand === "routes" && (
        <div className="border-t border-slate-800">
          {ascents.map((ascent) => (
            <AscentRow key={ascent.id} ascent={ascent} />
          ))}
        </div>
      )}
    </div>
  );
}

function AscentRow({ ascent }: { ascent: FeedSessionAscent }) {
  return (
    <div className="flex items-center gap-3 border-b border-slate-800/50 px-4 py-2 last:border-b-0">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="truncate text-sm text-slate-200">
            {ascent.route_name ?? "Unnamed route"}
          </span>
          {ascent.grade && (
            <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 font-mono text-xs font-medium text-slate-300">
              {ascent.grade}
            </span>
          )}
          <span
            className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
              TICK_COLORS[ascent.tick_type] ?? TICK_COLORS.attempt
            }`}
          >
            {tickTypeLabel(ascent.tick_type)}
          </span>
        </div>
      </div>
      {ascent.tries != null && (
        <span className="shrink-0 text-[11px] text-slate-500">
          {ascent.tries} {ascent.tries === 1 ? "try" : "tries"}
        </span>
      )}
    </div>
  );
}
