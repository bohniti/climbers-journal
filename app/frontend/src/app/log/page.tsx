"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchFeed,
  type FeedItem,
  type FeedSessionData,
  type FeedSessionAscent,
  type ActivityResponse,
} from "@/lib/api";
import {
  TICK_COLORS,
  tickTypeLabel,
  formatDuration,
  formatDate,
  formatDistance,
  sportCategory,
} from "@/lib/constants";
import ActivityIcon from "@/components/ActivityIcon";
import SessionEditModal from "@/components/SessionEditModal";
import AscentEditModal from "@/components/AscentEditModal";
import EnduranceEditModal from "@/components/EnduranceEditModal";

// ── Filter state ──────────────────────────────────────────────────────

interface Filters {
  activityType: "all" | "climbing" | "endurance";
  dateFrom: string;
  dateTo: string;
}

const PAGE_SIZE = 20;

// ── Component ─────────────────────────────────────────────────────────

export default function LogPage() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [filters, setFilters] = useState<Filters>({
    activityType: "all",
    dateFrom: "",
    dateTo: "",
  });

  const fetchItems = useCallback(
    async (currentOffset: number, append: boolean) => {
      setLoading(true);
      setError(null);

      try {
        const feed = await fetchFeed({
          type: filters.activityType,
          offset: currentOffset,
          limit: PAGE_SIZE,
        });

        setHasMore(feed.length === PAGE_SIZE);
        setOffset(currentOffset + feed.length);

        if (append) {
          setItems((prev) => [...prev, ...feed]);
        } else {
          setItems(feed);
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
    setOffset(0);
    fetchItems(0, false);
  }, [fetchItems]);

  const loadMore = () => {
    fetchItems(offset, true);
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
              })
            }
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
          >
            <option value="all">All activities</option>
            <option value="climbing">Climbing</option>
            <option value="endurance">Endurance</option>
          </select>

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
            filters.dateFrom ||
            filters.dateTo) && (
            <button
              onClick={() =>
                setFilters({
                  activityType: "all",
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
              item.kind === "session" ? (
                <ClimbingSessionCard
                  key={`s-${item.data.id}`}
                  session={item.data}
                  onRefresh={() => {
                    setOffset(0);
                    fetchItems(0, false);
                  }}
                />
              ) : (
                <EnduranceCard
                  key={`e-${item.data.id}`}
                  activity={item.data}
                  onRefresh={() => {
                    setOffset(0);
                    fetchItems(0, false);
                  }}
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

// ── Climbing Session Card ─────────────────────────────────────────────

type ExpandLevel = "collapsed" | "summary" | "routes";

function ClimbingSessionCard({
  session,
  onRefresh,
}: {
  session: FeedSessionData;
  onRefresh: () => void;
}) {
  const defaultLevel: ExpandLevel =
    session.ascent_count > 10 ? "summary" : "collapsed";
  const [expand, setExpand] = useState<ExpandLevel>(defaultLevel);
  const [editSession, setEditSession] = useState(false);

  const cycleExpand = () => {
    if (expand === "collapsed") setExpand("summary");
    else if (expand === "summary") setExpand("routes");
    else setExpand("collapsed");
  };

  // Compute stats
  const ascents = session.ascents;
  const grades = ascents
    .map((a) => a.grade)
    .filter((g): g is string => g != null)
    .sort();
  const hardestGrade = grades.length > 0 ? grades[grades.length - 1] : null;

  const sends = ascents.filter(
    (a) =>
      a.tick_type !== "attempt" && a.tick_type !== "hang"
  );
  const attempts = ascents.filter(
    (a) => a.tick_type === "attempt" || a.tick_type === "hang"
  );

  // Tick type breakdown for pills
  const tickBreakdown: Record<string, number> = {};
  for (const a of ascents) {
    tickBreakdown[a.tick_type] = (tickBreakdown[a.tick_type] || 0) + 1;
  }

  // Duration from linked watch
  const linkedDuration = session.linked_activity?.duration_s;

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 text-left transition-colors hover:border-slate-600">
      {/* Collapsed header — always visible */}
      <div
        role="button"
        tabIndex={0}
        onClick={cycleExpand}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            cycleExpand();
          }
        }}
        className="w-full px-4 py-3"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-red-900/30">
            <ActivityIcon category="climbing" size="md" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Link
                href={`/crags/${session.crag_id}`}
                onClick={(e) => e.stopPropagation()}
                className="truncate text-sm font-medium text-slate-100 hover:text-emerald-400"
              >
                {session.crag_name ?? "Unknown crag"}
              </Link>
              {linkedDuration != null && (
                <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-400">
                  {formatDuration(linkedDuration)}
                </span>
              )}
            </div>
            <div className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-400">
              <span>{formatDate(session.date)}</span>
              <span>&middot;</span>
              <span>
                {session.ascent_count} route{session.ascent_count !== 1 ? "s" : ""}
              </span>
              {hardestGrade && (
                <>
                  <span>&middot;</span>
                  <span className="font-mono">{hardestGrade}</span>
                </>
              )}
            </div>
          </div>
          {/* Edit button */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setEditSession(true);
            }}
            className="shrink-0 rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-300"
            title="Edit session"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
            </svg>
          </button>
          {/* Tick type pills */}
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
      </div>

      {/* Summary level */}
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

          {/* Linked watch data */}
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

      {/* Routes level */}
      {expand === "routes" && (
        <div className="border-t border-slate-800">
          {ascents.map((ascent) => (
            <AscentRow key={ascent.id} ascent={ascent} onRefresh={onRefresh} />
          ))}
        </div>
      )}

      {/* Session edit modal */}
      {editSession && (
        <SessionEditModal
          session={session}
          onClose={() => setEditSession(false)}
          onSaved={() => {
            setEditSession(false);
            onRefresh();
          }}
        />
      )}
    </div>
  );
}

function AscentRow({
  ascent,
  onRefresh,
}: {
  ascent: FeedSessionAscent;
  onRefresh: () => void;
}) {
  const [editing, setEditing] = useState(false);

  return (
    <>
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
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="shrink-0 rounded p-1 text-slate-600 hover:bg-slate-800 hover:text-slate-400"
          title="Edit ascent"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
          </svg>
        </button>
      </div>
      {editing && (
        <AscentEditModal
          ascent={ascent}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            onRefresh();
          }}
        />
      )}
    </>
  );
}

// ── Endurance Card ────────────────────────────────────────────────────

function EnduranceCard({
  activity,
  onRefresh,
}: {
  activity: ActivityResponse;
  onRefresh: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);

  const toggleExpand = () => setExpanded((p) => !p);

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 text-left transition-colors hover:border-slate-600">
      <div
        role="button"
        tabIndex={0}
        onClick={toggleExpand}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggleExpand();
          }
        }}
        className="w-full px-4 py-3"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-900/30">
            <ActivityIcon category={sportCategory(activity.type)} size="md" />
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
          {/* Edit button */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setEditing(true);
            }}
            className="shrink-0 rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-300"
            title="Edit activity"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
            </svg>
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-slate-800 px-4 py-3 text-xs text-slate-400">
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

      {editing && (
        <EnduranceEditModal
          activity={activity}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            onRefresh();
          }}
        />
      )}
    </div>
  );
}
