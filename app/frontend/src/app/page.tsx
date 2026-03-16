"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchDashboard,
  fetchGradePyramid,
  type DashboardData,
  type GradePyramidEntry,
} from "@/lib/api";
import {
  TICK_COLORS,
  PYRAMID_COLORS,
  ACTIVITY_ICONS,
  tickTypeLabel,
  formatDuration,
  formatDate,
} from "@/lib/constants";

// ── Component ────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [venueFilter, setVenueFilter] = useState<string>("");
  const [periodFilter, setPeriodFilter] = useState<string>("");
  const [pyramid, setPyramid] = useState<GradePyramidEntry[]>([]);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await fetchDashboard();
      setData(d);
      setPyramid(d.grade_pyramid);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  // Refetch pyramid when filters change
  useEffect(() => {
    if (!venueFilter && !periodFilter && data) {
      setPyramid(data.grade_pyramid);
      return;
    }
    let cancelled = false;
    fetchGradePyramid({
      venue_type: venueFilter || undefined,
      period: periodFilter || undefined,
    }).then((p) => {
      if (!cancelled) setPyramid(p);
    });
    return () => {
      cancelled = true;
    };
  }, [venueFilter, periodFilter, data]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-400">
        Loading dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="rounded-lg border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      </div>
    );
  }

  if (!data) return null;

  const maxPyramidTotal = Math.max(...pyramid.map((e) => e.total), 1);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-6">
        {/* Quick actions */}
        <div className="mb-6 flex items-center gap-3">
          <Link
            href="/log/add"
            data-tour-step="log-session"
            className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600"
          >
            + Log session
          </Link>
          <Link
            href="/chat"
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800"
          >
            Ask Copilot
          </Link>
        </div>

        {/* Stats cards row */}
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2" data-tour-step="dashboard">
          {/* Climbing stats */}
          <div className="rounded-xl border border-slate-700 bg-slate-900 p-4">
            <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-slate-400">
              Climbing
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-2xl font-bold text-slate-100">
                  {data.climbing_stats.total_sends_week}
                </div>
                <div className="text-xs text-slate-400">
                  sends this week
                </div>
              </div>
              <div>
                <div className="text-2xl font-bold text-slate-100">
                  {data.climbing_stats.total_sends_month}
                </div>
                <div className="text-xs text-slate-400">
                  sends this month
                </div>
              </div>
            </div>
            {data.climbing_stats.hardest_send && (
              <div className="mt-3 border-t border-slate-800 pt-3">
                <div className="text-xs text-slate-400">
                  Hardest send
                </div>
                <div className="mt-0.5 text-sm font-medium text-slate-100">
                  {data.climbing_stats.hardest_send.route_name ?? "Unnamed"}{" "}
                  <span className="font-mono text-xs">
                    {data.climbing_stats.hardest_send.grade}
                  </span>
                </div>
                <div className="text-xs text-slate-400">
                  {data.climbing_stats.hardest_send.crag_name}
                </div>
              </div>
            )}
          </div>

          {/* Endurance stats */}
          <div className="rounded-xl border border-slate-700 bg-slate-900 p-4">
            <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-slate-400">
              Endurance (this week)
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-2xl font-bold text-slate-100">
                  {data.endurance_stats.activities_week}
                </div>
                <div className="text-xs text-slate-400">
                  activities
                </div>
              </div>
              <div>
                <div className="text-2xl font-bold text-slate-100">
                  {data.endurance_stats.total_duration_min_week > 0
                    ? `${Math.floor(data.endurance_stats.total_duration_min_week / 60)}h ${data.endurance_stats.total_duration_min_week % 60}m`
                    : "0m"}
                </div>
                <div className="text-xs text-slate-400">
                  total time
                </div>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-4 border-t border-slate-800 pt-3">
              <div>
                <div className="text-sm font-medium text-slate-100">
                  {data.endurance_stats.total_distance_km_week} km
                </div>
                <div className="text-xs text-slate-400">
                  distance
                </div>
              </div>
              <div>
                <div className="text-sm font-medium text-slate-100">
                  {Math.round(data.endurance_stats.total_training_load_week)}
                </div>
                <div className="text-xs text-slate-400">
                  training load
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Grade Pyramid */}
        <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Grade Pyramid
            </h3>
            <div className="flex gap-2">
              <select
                value={venueFilter}
                onChange={(e) => setVenueFilter(e.target.value)}
                className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-300"
              >
                <option value="">All venues</option>
                <option value="outdoor_crag">Outdoor</option>
                <option value="indoor_gym">Indoor</option>
              </select>
              <select
                value={periodFilter}
                onChange={(e) => setPeriodFilter(e.target.value)}
                className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-xs text-slate-300"
              >
                <option value="">All time</option>
                <option value="this_year">This year</option>
                <option value="this_month">This month</option>
              </select>
            </div>
          </div>

          {/* Legend */}
          <div className="mb-3 flex flex-wrap gap-3 text-[10px]">
            {(["onsight", "flash", "redpoint", "pinkpoint", "repeat"] as const).map(
              (tt) => (
                <div key={tt} className="flex items-center gap-1">
                  <div
                    className={`h-2.5 w-2.5 rounded-sm ${PYRAMID_COLORS[tt]}`}
                  />
                  <span className="text-slate-400">
                    {tickTypeLabel(tt)}
                  </span>
                </div>
              )
            )}
          </div>

          {pyramid.length === 0 ? (
            <div className="py-8 text-center text-sm text-slate-500">
              No sends yet. Start logging!
            </div>
          ) : (
            <div className="space-y-1.5">
              {pyramid.map((entry) => (
                <div key={entry.grade} className="flex items-center gap-2">
                  <div className="w-10 shrink-0 text-right font-mono text-xs font-medium text-slate-300">
                    {entry.grade}
                  </div>
                  <div className="flex flex-1 items-center">
                    <div
                      className="flex h-5 overflow-hidden rounded"
                      style={{
                        width: `${Math.max(
                          (entry.total / maxPyramidTotal) * 100,
                          2
                        )}%`,
                      }}
                    >
                      {(
                        ["onsight", "flash", "redpoint", "pinkpoint", "repeat"] as const
                      ).map(
                        (tt) =>
                          entry[tt] > 0 && (
                            <div
                              key={tt}
                              className={`${PYRAMID_COLORS[tt]}`}
                              style={{
                                width: `${(entry[tt] / entry.total) * 100}%`,
                              }}
                              title={`${tickTypeLabel(tt)}: ${entry[tt]}`}
                            />
                          )
                      )}
                    </div>
                    <span className="ml-1.5 text-[10px] text-slate-400">
                      {entry.total}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Activity Feed */}
        <div className="rounded-xl border border-slate-700 bg-slate-900 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Last 7 days
            </h3>
            <Link
              href="/log"
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              View all
            </Link>
          </div>

          {data.recent_climbing.length === 0 &&
          data.recent_endurance.length === 0 ? (
            <div className="py-6 text-center text-sm text-slate-500">
              No activity this week
            </div>
          ) : (
            <div className="space-y-1.5">
              {mergeRecent(data.recent_climbing, data.recent_endurance).map(
                (item) =>
                  item.kind === "climbing" ? (
                    <div
                      key={`c-${item.data.id}`}
                      className="flex items-center gap-3 rounded-lg px-2 py-1.5"
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-red-900/30 text-sm">
                        {"\u{1F9D7}"}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="truncate text-sm text-slate-100">
                            {item.data.route_name ?? "Unnamed"}
                          </span>
                          {item.data.grade && (
                            <span className="shrink-0 font-mono text-xs text-slate-400">
                              {item.data.grade}
                            </span>
                          )}
                          <span
                            className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                              TICK_COLORS[item.data.tick_type] ??
                              TICK_COLORS.attempt
                            }`}
                          >
                            {tickTypeLabel(item.data.tick_type)}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {item.data.crag_name} &middot;{" "}
                          {formatDate(item.data.date)}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div
                      key={`e-${item.data.id}`}
                      className="flex items-center gap-3 rounded-lg px-2 py-1.5"
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-blue-900/30 text-sm">
                        {ACTIVITY_ICONS[item.data.type] ?? "\u{1F4AA}"}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="truncate text-sm text-slate-100">
                            {item.data.name ?? item.data.type}
                          </span>
                          <span className="shrink-0 text-xs text-slate-400">
                            {formatDuration(item.data.duration_s)}
                          </span>
                          {item.data.distance_m != null &&
                            item.data.distance_m > 0 && (
                              <span className="shrink-0 text-xs text-slate-400">
                                {(item.data.distance_m / 1000).toFixed(1)} km
                              </span>
                            )}
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {item.data.type} &middot; {formatDate(item.data.date)}
                        </div>
                      </div>
                    </div>
                  )
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Merge recent items by date ───────────────────────────────────────

type MergedItem =
  | {
      kind: "climbing";
      date: string;
      data: DashboardData["recent_climbing"][number];
    }
  | {
      kind: "endurance";
      date: string;
      data: DashboardData["recent_endurance"][number];
    };

function mergeRecent(
  climbing: DashboardData["recent_climbing"],
  endurance: DashboardData["recent_endurance"]
): MergedItem[] {
  const items: MergedItem[] = [
    ...climbing.map(
      (c) => ({ kind: "climbing" as const, date: c.date, data: c })
    ),
    ...endurance.map(
      (e) => ({ kind: "endurance" as const, date: e.date, data: e })
    ),
  ];
  items.sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );
  return items;
}
