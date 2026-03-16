"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  listAscents,
  listActivities,
  type AscentResponse,
  type ActivityResponse,
} from "@/lib/api";
import {
  TICK_COLORS,
  tickTypeLabel,
  formatDuration,
  formatDate,
  formatDistance,
  sportIcon,
} from "@/lib/constants";

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

        let merged = [...climbingItems, ...enduranceItems].sort(
          (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
        );

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
      <div className="shrink-0 border-b border-slate-700 bg-slate-900 px-4 py-3">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-3">
          <Link
            href="/log/add"
            className="rounded-lg bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-600"
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
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
          >
            <option value="all">All activities</option>
            <option value="climbing">Climbing</option>
            <option value="endurance">Endurance</option>
          </select>

          {/* Tick type */}
          {filters.activityType !== "endurance" && (
            <select
              value={filters.tickType}
              onChange={(e) => updateFilter({ tickType: e.target.value })}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
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
              className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-sm text-slate-100"
            />
            <span className="text-xs text-slate-400">&ndash;</span>
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => updateFilter({ dateTo: e.target.value })}
              className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-sm text-slate-100"
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
              className="text-xs text-slate-400 hover:text-slate-200"
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
            <div className="mb-4 rounded-lg border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          {!loading && items.length === 0 && (
            <div className="pt-24 text-center text-slate-500">
              <p className="text-lg">No activities yet</p>
              <p className="mt-1 text-sm">
                <Link
                  href="/log/add"
                  className="underline hover:text-slate-300"
                >
                  Log a climbing session
                </Link>{" "}
                or use the{" "}
                <Link
                  href="/chat"
                  className="underline hover:text-slate-300"
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
            <div className="py-8 text-center text-sm text-slate-400">
              Loading...
            </div>
          )}
          {!loading && hasMore && items.length > 0 && (
            <div className="py-6 text-center">
              <button
                onClick={loadMore}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-800"
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
      className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-left transition-colors hover:border-slate-600"
    >
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-red-900/30 text-lg">
          {"\u{1F9D7}"}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium text-slate-100">
              {ascent.route_name ?? "Unnamed route"}
            </span>
            {ascent.grade && (
              <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-xs font-mono font-medium text-slate-300">
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
          <div className="mt-0.5 text-xs text-slate-400">
            {ascent.crag_name} &middot; {formatDate(ascent.date)}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 border-t border-slate-800 pt-3 text-xs text-slate-400">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {ascent.tries != null && (
              <>
                <span className="text-slate-500">Tries</span>
                <span>{ascent.tries}</span>
              </>
            )}
            {ascent.rating != null && (
              <>
                <span className="text-slate-500">Rating</span>
                <span>{"*".repeat(ascent.rating)}</span>
              </>
            )}
            {ascent.partner && (
              <>
                <span className="text-slate-500">Partner</span>
                <span>{ascent.partner}</span>
              </>
            )}
          </div>
          {ascent.notes && (
            <p className="mt-2 text-slate-400">
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
      className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-left transition-colors hover:border-slate-600"
    >
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-900/30 text-lg">
          {sportIcon(activity.type)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium text-slate-100">
              {activity.name ?? activity.type}
            </span>
            <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-400">
              {formatDuration(activity.duration_s)}
            </span>
            {activity.distance_m != null && activity.distance_m > 0 && (
              <span className="shrink-0 text-xs text-slate-400">
                {formatDistance(activity.distance_m)}
              </span>
            )}
          </div>
          <div className="mt-0.5 text-xs text-slate-400">
            {activity.type} &middot; {formatDate(activity.date)}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 border-t border-slate-800 pt-3 text-xs text-slate-400">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {activity.elevation_gain_m != null && (
              <>
                <span className="text-slate-500">Elevation</span>
                <span>{Math.round(activity.elevation_gain_m)} m</span>
              </>
            )}
            {activity.avg_hr != null && (
              <>
                <span className="text-slate-500">Avg HR</span>
                <span>{activity.avg_hr} bpm</span>
              </>
            )}
            {activity.max_hr != null && (
              <>
                <span className="text-slate-500">Max HR</span>
                <span>{activity.max_hr} bpm</span>
              </>
            )}
            {activity.training_load != null && (
              <>
                <span className="text-slate-500">Training load</span>
                <span>{Math.round(activity.training_load)}</span>
              </>
            )}
          </div>
        </div>
      )}
    </button>
  );
}
