"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  listAscents,
  listActivities,
  type AscentResponse,
  type ActivityResponse,
} from "@/lib/api";

// ── Unified activity item ─────────────────────────────────────────────

type LogItem =
  | { kind: "climbing"; date: string; data: AscentResponse }
  | { kind: "endurance"; date: string; data: ActivityResponse };

// ── Filter state ──────────────────────────────────────────────────────

interface Filters {
  activityType: "all" | "climbing" | "endurance";
  tickType: string;
  dateFrom: string;
  dateTo: string;
}

const TICK_TYPES = [
  "onsight",
  "flash",
  "redpoint",
  "pinkpoint",
  "repeat",
  "attempt",
  "hang",
];

const PAGE_SIZE = 30;

// ── Helpers ───────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatDistance(meters: number): string {
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
  return `${Math.round(meters)} m`;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

const ACTIVITY_ICONS: Record<string, string> = {
  Run: "\u{1F3C3}",
  Ride: "\u{1F6B4}",
  Hike: "\u{1F6B6}",
  TrailRun: "\u{26F0}",
  Swim: "\u{1F3CA}",
  Walk: "\u{1F6B6}",
  VirtualRide: "\u{1F6B4}",
};

function activityIcon(type: string): string {
  return ACTIVITY_ICONS[type] ?? "\u{1F4AA}";
}

function tickTypeLabel(tt: string): string {
  return tt.charAt(0).toUpperCase() + tt.slice(1);
}

const TICK_COLORS: Record<string, string> = {
  onsight:
    "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  flash:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300",
  redpoint:
    "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  pinkpoint:
    "bg-pink-100 text-pink-800 dark:bg-pink-900/40 dark:text-pink-300",
  repeat:
    "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  attempt:
    "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
  hang: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
};

// ── Component ─────────────────────────────────────────────────────────

export default function LogPage() {
  const [items, setItems] = useState<LogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [climbingOffset, setClimbingOffset] = useState(0);
  const [enduranceOffset, setEnduranceOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [filters, setFilters] = useState<Filters>({
    activityType: "all",
    tickType: "",
    dateFrom: "",
    dateTo: "",
  });

  const fetchItems = useCallback(
    async (cOffset: number, eOffset: number, append: boolean) => {
      setLoading(true);
      setError(null);

      try {
        const dateFilters = {
          date_from: filters.dateFrom || undefined,
          date_to: filters.dateTo || undefined,
        };

        const fetchClimbing =
          filters.activityType === "all" ||
          filters.activityType === "climbing";
        const fetchEndurance =
          (filters.activityType === "all" ||
            filters.activityType === "endurance") &&
          !filters.tickType;

        const [ascents, activities] = await Promise.all([
          fetchClimbing
            ? listAscents({
                ...dateFilters,
                tick_type: filters.tickType || undefined,
                offset: cOffset,
                limit: PAGE_SIZE,
              })
            : Promise.resolve([]),
          fetchEndurance
            ? listActivities({
                ...dateFilters,
                offset: eOffset,
                limit: PAGE_SIZE,
              })
            : Promise.resolve([]),
        ]);

        const climbingItems: LogItem[] = ascents.map((a) => ({
          kind: "climbing",
          date: a.date,
          data: a,
        }));
        const enduranceItems: LogItem[] = activities.map((a) => ({
          kind: "endurance",
          date: a.date,
          data: a,
        }));

        // Merge and sort by date descending
        let merged = [...climbingItems, ...enduranceItems].sort(
          (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
        );

        // For mixed feeds, take PAGE_SIZE items and track how many
        // of each type were consumed so offsets advance correctly
        if (merged.length > PAGE_SIZE) {
          merged = merged.slice(0, PAGE_SIZE);
        }

        const usedClimbing = merged.filter(
          (i) => i.kind === "climbing"
        ).length;
        const usedEndurance = merged.filter(
          (i) => i.kind === "endurance"
        ).length;
        setClimbingOffset(cOffset + usedClimbing);
        setEnduranceOffset(eOffset + usedEndurance);

        setHasMore(
          (fetchClimbing && ascents.length === PAGE_SIZE) ||
            (fetchEndurance && activities.length === PAGE_SIZE)
        );

        if (append) {
          setItems((prev) => [...prev, ...merged]);
        } else {
          setItems(merged);
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load activities"
        );
      } finally {
        setLoading(false);
      }
    },
    [filters]
  );

  // Reset offsets and refetch when filters change
  useEffect(() => {
    setClimbingOffset(0);
    setEnduranceOffset(0);
    fetchItems(0, 0, false);
  }, [fetchItems]);

  const loadMore = () => {
    fetchItems(climbingOffset, enduranceOffset, true);
  };

  const updateFilter = (updates: Partial<Filters>) => {
    setFilters((prev) => ({ ...prev, ...updates }));
  };

  return (
    <div className="flex h-full flex-col">
      {/* Filter bar */}
      <div className="shrink-0 border-b border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-3">
          <Link
            href="/log/add"
            className="rounded-lg bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            + Log session
          </Link>
          {/* Activity type */}
          <select
            value={filters.activityType}
            onChange={(e) =>
              updateFilter({
                activityType: e.target.value as Filters["activityType"],
                tickType:
                  e.target.value === "endurance" ? "" : filters.tickType,
              })
            }
            className="rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
          >
            <option value="all">All activities</option>
            <option value="climbing">Climbing</option>
            <option value="endurance">Endurance</option>
          </select>

          {/* Tick type (only when climbing visible) */}
          {filters.activityType !== "endurance" && (
            <select
              value={filters.tickType}
              onChange={(e) => updateFilter({ tickType: e.target.value })}
              className="rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
            >
              <option value="">All tick types</option>
              {TICK_TYPES.map((t) => (
                <option key={t} value={t}>
                  {tickTypeLabel(t)}
                </option>
              ))}
            </select>
          )}

          {/* Date range */}
          <div className="flex items-center gap-1.5">
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => updateFilter({ dateFrom: e.target.value })}
              className="rounded-lg border border-zinc-300 bg-zinc-50 px-2.5 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
            />
            <span className="text-xs text-zinc-400">&ndash;</span>
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => updateFilter({ dateTo: e.target.value })}
              className="rounded-lg border border-zinc-300 bg-zinc-50 px-2.5 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
            />
          </div>

          {/* Clear filters */}
          {(filters.activityType !== "all" ||
            filters.tickType ||
            filters.dateFrom ||
            filters.dateTo) && (
            <button
              onClick={() =>
                setFilters({
                  activityType: "all",
                  tickType: "",
                  dateFrom: "",
                  dateTo: "",
                })
              }
              className="text-xs text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Activity list */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-4">
          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
              {error}
            </div>
          )}

          {!loading && items.length === 0 && (
            <div className="pt-24 text-center text-zinc-400 dark:text-zinc-600">
              <p className="text-lg">No activities yet</p>
              <p className="mt-1 text-sm">
                <Link
                  href="/log/add"
                  className="underline hover:text-zinc-600 dark:hover:text-zinc-300"
                >
                  Log a climbing session
                </Link>{" "}
                or use the{" "}
                <Link
                  href="/chat"
                  className="underline hover:text-zinc-600 dark:hover:text-zinc-300"
                >
                  Copilot
                </Link>
              </p>
            </div>
          )}

          <div className="space-y-2">
            {items.map((item) =>
              item.kind === "climbing" ? (
                <ClimbingCard
                  key={`c-${item.data.id}`}
                  ascent={item.data}
                />
              ) : (
                <EnduranceCard
                  key={`e-${item.data.id}`}
                  activity={item.data}
                />
              )
            )}
          </div>

          {/* Pagination */}
          {loading && (
            <div className="py-8 text-center text-sm text-zinc-400">
              Loading...
            </div>
          )}
          {!loading && hasMore && items.length > 0 && (
            <div className="py-6 text-center">
              <button
                onClick={loadMore}
                className="rounded-lg border border-zinc-300 px-4 py-2 text-sm text-zinc-700 transition-colors hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800"
              >
                Load more
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Card components ───────────────────────────────────────────────────

function ClimbingCard({ ascent }: { ascent: AscentResponse }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <button
      type="button"
      onClick={() => setExpanded((p) => !p)}
      className="w-full rounded-xl border border-zinc-200 bg-white px-4 py-3 text-left transition-colors hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-700"
    >
      <div className="flex items-center gap-3">
        {/* Icon */}
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-red-100 text-lg dark:bg-red-900/30">
          {"\u{1F9D7}"}
        </div>

        {/* Main info */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
              {ascent.route_name ?? "Unnamed route"}
            </span>
            {ascent.grade && (
              <span className="shrink-0 rounded bg-zinc-100 px-1.5 py-0.5 text-xs font-mono font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                {ascent.grade}
              </span>
            )}
            <span
              className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                TICK_COLORS[ascent.tick_type] ?? TICK_COLORS.attempt
              }`}
            >
              {tickTypeLabel(ascent.tick_type)}
            </span>
          </div>
          <div className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            {ascent.crag_name} &middot; {formatDate(ascent.date)}
          </div>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-3 border-t border-zinc-100 pt-3 text-xs text-zinc-600 dark:border-zinc-800 dark:text-zinc-400">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {ascent.tries != null && (
              <>
                <span className="text-zinc-400">Tries</span>
                <span>{ascent.tries}</span>
              </>
            )}
            {ascent.rating != null && (
              <>
                <span className="text-zinc-400">Rating</span>
                <span>{"*".repeat(ascent.rating)}</span>
              </>
            )}
            {ascent.partner && (
              <>
                <span className="text-zinc-400">Partner</span>
                <span>{ascent.partner}</span>
              </>
            )}
          </div>
          {ascent.notes && (
            <p className="mt-2 text-zinc-500 dark:text-zinc-400">
              {ascent.notes}
            </p>
          )}
        </div>
      )}
    </button>
  );
}

function EnduranceCard({ activity }: { activity: ActivityResponse }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <button
      type="button"
      onClick={() => setExpanded((p) => !p)}
      className="w-full rounded-xl border border-zinc-200 bg-white px-4 py-3 text-left transition-colors hover:border-zinc-300 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-700"
    >
      <div className="flex items-center gap-3">
        {/* Icon */}
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-lg dark:bg-blue-900/30">
          {activityIcon(activity.type)}
        </div>

        {/* Main info */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100">
              {activity.name ?? activity.type}
            </span>
            <span className="shrink-0 rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
              {formatDuration(activity.duration_s)}
            </span>
            {activity.distance_m != null && activity.distance_m > 0 && (
              <span className="shrink-0 text-xs text-zinc-500 dark:text-zinc-400">
                {formatDistance(activity.distance_m)}
              </span>
            )}
          </div>
          <div className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
            {activity.type} &middot; {formatDate(activity.date)}
          </div>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="mt-3 border-t border-zinc-100 pt-3 text-xs text-zinc-600 dark:border-zinc-800 dark:text-zinc-400">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {activity.elevation_gain_m != null && (
              <>
                <span className="text-zinc-400">Elevation</span>
                <span>{Math.round(activity.elevation_gain_m)} m</span>
              </>
            )}
            {activity.avg_hr != null && (
              <>
                <span className="text-zinc-400">Avg HR</span>
                <span>{activity.avg_hr} bpm</span>
              </>
            )}
            {activity.max_hr != null && (
              <>
                <span className="text-zinc-400">Max HR</span>
                <span>{activity.max_hr} bpm</span>
              </>
            )}
            {activity.training_load != null && (
              <>
                <span className="text-zinc-400">Training load</span>
                <span>{Math.round(activity.training_load)}</span>
              </>
            )}
          </div>
        </div>
      )}
    </button>
  );
}
