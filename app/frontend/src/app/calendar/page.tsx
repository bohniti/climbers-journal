"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchCalendar,
  type CalendarData,
  type CalendarDayEntry,
} from "@/lib/api";

// ── Helpers ──────────────────────────────────────────────────────────

const ACTIVITY_ICONS: Record<string, string> = {
  Run: "\u{1F3C3}",
  Ride: "\u{1F6B4}",
  Hike: "\u{1F6B6}",
  TrailRun: "\u{26F0}",
  Swim: "\u{1F3CA}",
  Walk: "\u{1F6B6}",
  VirtualRide: "\u{1F6B4}",
};

const VENUE_COLORS: Record<string, string> = {
  outdoor_crag: "text-red-600 dark:text-red-400",
  indoor_gym: "text-violet-600 dark:text-violet-400",
  mixed: "text-orange-600 dark:text-orange-400",
};

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h${m > 0 ? ` ${m}m` : ""}`;
  return `${m}m`;
}

function monthStr(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, "0")}`;
}

function monthLabel(year: number, month: number): string {
  const d = new Date(year, month - 1, 1);
  return d.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function getMonthGrid(year: number, month: number): (number | null)[][] {
  // ISO weekday: Mon=0 ... Sun=6
  const firstDay = new Date(year, month - 1, 1);
  const startDow = (firstDay.getDay() + 6) % 7; // convert Sun=0 to Mon=0
  const daysInMonth = new Date(year, month, 0).getDate();

  const weeks: (number | null)[][] = [];
  let week: (number | null)[] = new Array(startDow).fill(null);
  for (let d = 1; d <= daysInMonth; d++) {
    week.push(d);
    if (week.length === 7) {
      weeks.push(week);
      week = [];
    }
  }
  if (week.length > 0) {
    while (week.length < 7) week.push(null);
    weeks.push(week);
  }
  return weeks;
}

function getWeekDates(
  year: number,
  month: number,
  weekIndex: number,
  grid: (number | null)[][]
): { day: number; dateStr: string }[] {
  return grid[weekIndex]
    .filter((d): d is number => d !== null)
    .map((d) => ({
      day: d,
      dateStr: `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`,
    }));
}

// ── Component ────────────────────────────────────────────────────────

type ViewMode = "month" | "week";

export default function CalendarPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [view, setView] = useState<ViewMode>("month");
  const [weekIndex, setWeekIndex] = useState(0);
  const [data, setData] = useState<CalendarData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const grid = getMonthGrid(year, month);

  // Set initial week to current week
  useEffect(() => {
    const today = now.getDate();
    const idx = grid.findIndex((w) => w.includes(today));
    if (idx >= 0) setWeekIndex(idx);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const d = await fetchCalendar(monthStr(year, month));
      setData(d);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load calendar");
    } finally {
      setLoading(false);
    }
  }, [year, month]);

  useEffect(() => {
    load();
  }, [load]);

  const dayMap = new Map<string, CalendarDayEntry>();
  if (data) {
    for (const d of data.days) {
      dayMap.set(d.date, d);
    }
  }

  function prevMonth() {
    if (month === 1) {
      setYear(year - 1);
      setMonth(12);
    } else {
      setMonth(month - 1);
    }
    setWeekIndex(0);
  }

  function nextMonth() {
    if (month === 12) {
      setYear(year + 1);
      setMonth(1);
    } else {
      setMonth(month + 1);
    }
    setWeekIndex(0);
  }

  function goToday() {
    const t = new Date();
    setYear(t.getFullYear());
    setMonth(t.getMonth() + 1);
    const g = getMonthGrid(t.getFullYear(), t.getMonth() + 1);
    const idx = g.findIndex((w) => w.includes(t.getDate()));
    setWeekIndex(idx >= 0 ? idx : 0);
  }

  const isToday = (day: number) => {
    const t = new Date();
    return t.getFullYear() === year && t.getMonth() + 1 === month && t.getDate() === day;
  };

  function dateStr(day: number): string {
    return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }

  // ── Render helpers ──

  function renderDayCell(day: number | null, compact: boolean) {
    if (day === null) {
      return (
        <div
          key={`empty-${Math.random()}`}
          className="min-h-[4.5rem] rounded-lg border border-transparent"
        />
      );
    }

    const ds = dateStr(day);
    const entry = dayMap.get(ds);
    const hasActivity = !!entry;
    const today = isToday(day);

    return (
      <Link
        key={day}
        href={`/log?date_from=${ds}&date_to=${ds}`}
        className={`group relative flex min-h-[4.5rem] flex-col rounded-lg border p-1.5 transition-colors ${
          hasActivity
            ? "border-zinc-200 bg-white hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-zinc-600"
            : "border-zinc-100 bg-zinc-50/50 hover:border-zinc-200 dark:border-zinc-800/50 dark:bg-zinc-950/30 dark:hover:border-zinc-700"
        }`}
      >
        {/* Day number */}
        <div className="mb-0.5 flex items-center justify-between">
          <span
            className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-medium ${
              today
                ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                : hasActivity
                  ? "text-zinc-900 dark:text-zinc-100"
                  : "text-zinc-400 dark:text-zinc-600"
            }`}
          >
            {day}
          </span>
        </div>

        {/* Climbing info */}
        {entry?.climbing && (
          <div className="flex items-center gap-1">
            <span className="text-[10px]">{"\u{1F9D7}"}</span>
            <span
              className={`text-[10px] font-medium ${VENUE_COLORS[entry.climbing.venue_type] ?? "text-zinc-600 dark:text-zinc-400"}`}
            >
              {entry.climbing.route_count}
              {!compact && entry.climbing.hardest_grade && (
                <span className="ml-0.5 font-mono">
                  ({entry.climbing.hardest_grade})
                </span>
              )}
            </span>
          </div>
        )}

        {/* Endurance info */}
        {entry?.endurance &&
          (compact ? (
            <div className="flex items-center gap-0.5">
              {entry.endurance.activities.slice(0, 3).map((a, i) => (
                <span key={i} className="text-[10px]">
                  {ACTIVITY_ICONS[a.type] ?? "\u{1F4AA}"}
                </span>
              ))}
              {entry.endurance.activities.length > 3 && (
                <span className="text-[9px] text-zinc-400">
                  +{entry.endurance.activities.length - 3}
                </span>
              )}
            </div>
          ) : (
            <div className="space-y-px">
              {entry.endurance.activities.map((a, i) => (
                <div key={i} className="flex items-center gap-1">
                  <span className="text-[10px]">
                    {ACTIVITY_ICONS[a.type] ?? "\u{1F4AA}"}
                  </span>
                  <span className="text-[10px] text-zinc-500 dark:text-zinc-400">
                    {formatDuration(a.duration_s)}
                  </span>
                </div>
              ))}
            </div>
          ))}

        {/* Rest day indicator */}
        {!hasActivity && (
          <div className="mt-auto text-[9px] text-zinc-300 dark:text-zinc-700">
            rest
          </div>
        )}
      </Link>
    );
  }

  // ── Week view detail row ──

  function renderWeekDetail() {
    if (weekIndex >= grid.length) return null;
    const days = getWeekDates(year, month, weekIndex, grid);

    return (
      <div className="mt-4 space-y-2">
        {days.map(({ day, dateStr: ds }) => {
          const entry = dayMap.get(ds);
          const today = isToday(day);
          const d = new Date(ds + "T00:00:00");
          const label = d.toLocaleDateString(undefined, {
            weekday: "long",
            month: "short",
            day: "numeric",
          });

          return (
            <Link
              key={day}
              href={`/log?date_from=${ds}&date_to=${ds}`}
              className={`block rounded-xl border p-3 transition-colors hover:border-zinc-300 dark:hover:border-zinc-600 ${
                entry
                  ? "border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900"
                  : "border-zinc-100 bg-zinc-50/50 dark:border-zinc-800/50 dark:bg-zinc-950/30"
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
                    today
                      ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                      : "text-zinc-700 dark:text-zinc-300"
                  }`}
                >
                  {day}
                </span>
                <span className="text-sm text-zinc-500 dark:text-zinc-400">
                  {label}
                </span>
              </div>

              {!entry && (
                <div className="mt-1.5 text-xs text-zinc-400 dark:text-zinc-600">
                  Rest day
                </div>
              )}

              {entry?.climbing && (
                <div className="mt-2 flex items-center gap-2">
                  <span>{"\u{1F9D7}"}</span>
                  <span
                    className={`text-sm font-medium ${VENUE_COLORS[entry.climbing.venue_type] ?? ""}`}
                  >
                    {entry.climbing.route_count} route
                    {entry.climbing.route_count !== 1 ? "s" : ""}
                  </span>
                  {entry.climbing.hardest_grade && (
                    <span className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-xs text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
                      hardest: {entry.climbing.hardest_grade}
                    </span>
                  )}
                  <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
                    {entry.climbing.venue_type === "indoor_gym"
                      ? "gym"
                      : entry.climbing.venue_type === "mixed"
                        ? "mixed"
                        : "outdoor"}
                  </span>
                </div>
              )}

              {entry?.endurance && (
                <div className="mt-2 space-y-1">
                  {entry.endurance.activities.map((a, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <span>{ACTIVITY_ICONS[a.type] ?? "\u{1F4AA}"}</span>
                      <span className="text-sm text-zinc-700 dark:text-zinc-300">
                        {a.type}
                      </span>
                      <span className="text-sm text-zinc-500 dark:text-zinc-400">
                        {formatDuration(a.duration_s)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </Link>
          );
        })}
      </div>
    );
  }

  // ── Main render ──

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-6">
        {/* Header */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <button
              onClick={prevMonth}
              className="rounded-md border border-zinc-300 px-2 py-1 text-sm hover:bg-zinc-100 dark:border-zinc-600 dark:hover:bg-zinc-800"
            >
              &larr;
            </button>
            <h2 className="min-w-[10rem] text-center text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              {monthLabel(year, month)}
            </h2>
            <button
              onClick={nextMonth}
              className="rounded-md border border-zinc-300 px-2 py-1 text-sm hover:bg-zinc-100 dark:border-zinc-600 dark:hover:bg-zinc-800"
            >
              &rarr;
            </button>
            <button
              onClick={goToday}
              className="rounded-md border border-zinc-300 px-2 py-1 text-xs text-zinc-600 hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-400 dark:hover:bg-zinc-800"
            >
              Today
            </button>
          </div>

          <div className="flex gap-1 rounded-lg border border-zinc-200 p-0.5 dark:border-zinc-700">
            {(["month", "week"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  view === v
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                    : "text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
                }`}
              >
                {v.charAt(0).toUpperCase() + v.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {loading && (
          <div className="flex h-64 items-center justify-center text-sm text-zinc-400">
            Loading...
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}

        {!loading && !error && (
          <>
            {/* Weekday headers */}
            <div className="mb-1 grid grid-cols-7 gap-1">
              {WEEKDAYS.map((wd) => (
                <div
                  key={wd}
                  className="text-center text-[10px] font-medium uppercase tracking-wider text-zinc-400 dark:text-zinc-500"
                >
                  {wd}
                </div>
              ))}
            </div>

            {view === "month" ? (
              /* Month view: full grid */
              <div className="grid grid-cols-7 gap-1">
                {grid.flat().map((day, i) => (
                  <div key={i}>{renderDayCell(day, true)}</div>
                ))}
              </div>
            ) : (
              /* Week view: highlighted week + detail */
              <>
                {/* Week selector strip */}
                <div className="mb-2 flex gap-1">
                  {grid.map((_, i) => (
                    <button
                      key={i}
                      onClick={() => setWeekIndex(i)}
                      className={`flex-1 rounded-md py-1 text-[10px] font-medium transition-colors ${
                        weekIndex === i
                          ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                          : "bg-zinc-100 text-zinc-500 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700"
                      }`}
                    >
                      W{i + 1}
                    </button>
                  ))}
                </div>

                {/* Compact week grid */}
                <div className="grid grid-cols-7 gap-1">
                  {grid[weekIndex]?.map((day, i) => (
                    <div key={i}>{renderDayCell(day, false)}</div>
                  ))}
                </div>

                {/* Detailed list */}
                {renderWeekDetail()}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
