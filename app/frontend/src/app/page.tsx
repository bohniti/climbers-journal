"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchDashboard,
  fetchGradePyramid,
  type DashboardData,
  type GradePyramidEntry,
} from "@/lib/api";

// ── Helpers ──────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function tickTypeLabel(tt: string): string {
  return tt.charAt(0).toUpperCase() + tt.slice(1);
}

const TICK_COLORS: Record<string, string> = {
  onsight:
    "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  flash:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300",
  redpoint: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  pinkpoint:
    "bg-pink-100 text-pink-800 dark:bg-pink-900/40 dark:text-pink-300",
  repeat:
    "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  attempt: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
  hang: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
};

const ACTIVITY_ICONS: Record<string, string> = {
  Run: "\u{1F3C3}",
  Ride: "\u{1F6B4}",
  Hike: "\u{1F6B6}",
  TrailRun: "\u{26F0}",
  Swim: "\u{1F3CA}",
  Walk: "\u{1F6B6}",
  VirtualRide: "\u{1F6B4}",
};

const PYRAMID_COLORS: Record<string, string> = {
  onsight: "bg-amber-500 dark:bg-amber-400",
  flash: "bg-yellow-500 dark:bg-yellow-400",
  redpoint: "bg-red-500 dark:bg-red-400",
  pinkpoint: "bg-pink-500 dark:bg-pink-400",
  repeat: "bg-green-500 dark:bg-green-400",
};

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
      <div className="flex h-full items-center justify-center text-sm text-zinc-400">
        Loading dashboard...
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
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
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            + Log session
          </Link>
          <Link
            href="/chat"
            className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            Ask Copilot
          </Link>
        </div>

        {/* Stats cards row */}
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {/* Climbing stats */}
          <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
            <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Climbing
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                  {data.climbing_stats.total_sends_week}
                </div>
                <div className="text-xs text-zinc-500 dark:text-zinc-400">
                  sends this week
                </div>
              </div>
              <div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                  {data.climbing_stats.total_sends_month}
                </div>
                <div className="text-xs text-zinc-500 dark:text-zinc-400">
                  sends this month
                </div>
              </div>
            </div>
            {data.climbing_stats.hardest_send && (
              <div className="mt-3 border-t border-zinc-100 pt-3 dark:border-zinc-800">
                <div className="text-xs text-zinc-500 dark:text-zinc-400">
                  Hardest send
                </div>
                <div className="mt-0.5 text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {data.climbing_stats.hardest_send.route_name ?? "Unnamed"}{" "}
                  <span className="font-mono text-xs">
                    {data.climbing_stats.hardest_send.grade}
                  </span>
                </div>
                <div className="text-xs text-zinc-400">
                  {data.climbing_stats.hardest_send.crag_name}
                </div>
              </div>
            )}
          </div>

          {/* Endurance stats */}
          <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
            <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Endurance (this week)
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                  {data.endurance_stats.activities_week}
                </div>
                <div className="text-xs text-zinc-500 dark:text-zinc-400">
                  activities
                </div>
              </div>
              <div>
                <div className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                  {data.endurance_stats.total_duration_min_week > 0
                    ? `${Math.floor(data.endurance_stats.total_duration_min_week / 60)}h ${data.endurance_stats.total_duration_min_week % 60}m`
                    : "0m"}
                </div>
                <div className="text-xs text-zinc-500 dark:text-zinc-400">
                  total time
                </div>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-4 border-t border-zinc-100 pt-3 dark:border-zinc-800">
              <div>
                <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {data.endurance_stats.total_distance_km_week} km
                </div>
                <div className="text-xs text-zinc-500 dark:text-zinc-400">
                  distance
                </div>
              </div>
              <div>
                <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  {Math.round(data.endurance_stats.total_training_load_week)}
                </div>
                <div className="text-xs text-zinc-500 dark:text-zinc-400">
                  training load
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Grade Pyramid */}
        <div className="mb-6 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-xs font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Grade Pyramid
            </h3>
            <div className="flex gap-2">
              <select
                value={venueFilter}
                onChange={(e) => setVenueFilter(e.target.value)}
                className="rounded-md border border-zinc-300 bg-zinc-50 px-2 py-1 text-xs text-zinc-700 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
              >
                <option value="">All venues</option>
                <option value="outdoor_crag">Outdoor</option>
                <option value="indoor_gym">Indoor</option>
              </select>
              <select
                value={periodFilter}
                onChange={(e) => setPeriodFilter(e.target.value)}
                className="rounded-md border border-zinc-300 bg-zinc-50 px-2 py-1 text-xs text-zinc-700 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
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
                  <span className="text-zinc-500 dark:text-zinc-400">
                    {tickTypeLabel(tt)}
                  </span>
                </div>
              )
            )}
          </div>

          {pyramid.length === 0 ? (
            <div className="py-8 text-center text-sm text-zinc-400 dark:text-zinc-600">
              No sends yet. Start logging!
            </div>
          ) : (
            <div className="space-y-1.5">
              {pyramid.map((entry) => (
                <div key={entry.grade} className="flex items-center gap-2">
                  <div className="w-10 shrink-0 text-right font-mono text-xs font-medium text-zinc-700 dark:text-zinc-300">
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
                    <span className="ml-1.5 text-[10px] text-zinc-400">
                      {entry.total}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Activity Feed */}
        <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-xs font-medium uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Last 7 days
            </h3>
            <Link
              href="/log"
              className="text-xs text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
            >
              View all
            </Link>
          </div>

          {data.recent_climbing.length === 0 &&
          data.recent_endurance.length === 0 ? (
            <div className="py-6 text-center text-sm text-zinc-400 dark:text-zinc-600">
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
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-red-100 text-sm dark:bg-red-900/30">
                        {"\u{1F9D7}"}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="truncate text-sm text-zinc-900 dark:text-zinc-100">
                            {item.data.route_name ?? "Unnamed"}
                          </span>
                          {item.data.grade && (
                            <span className="shrink-0 font-mono text-xs text-zinc-500 dark:text-zinc-400">
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
                        <div className="text-[11px] text-zinc-400">
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
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-blue-100 text-sm dark:bg-blue-900/30">
                        {ACTIVITY_ICONS[item.data.type] ?? "\u{1F4AA}"}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="truncate text-sm text-zinc-900 dark:text-zinc-100">
                            {item.data.name ?? item.data.type}
                          </span>
                          <span className="shrink-0 text-xs text-zinc-500 dark:text-zinc-400">
                            {formatDuration(item.data.duration_s)}
                          </span>
                          {item.data.distance_m != null &&
                            item.data.distance_m > 0 && (
                              <span className="shrink-0 text-xs text-zinc-400">
                                {(item.data.distance_m / 1000).toFixed(1)} km
                              </span>
                            )}
                        </div>
                        <div className="text-[11px] text-zinc-400">
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
