"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchCalendar,
  type CalendarData,
  type CalendarDayEntry,
} from "@/lib/api";
import { VENUE_COLORS, formatDuration, sportCategory } from "@/lib/constants";
import ActivityIcon from "@/components/ActivityIcon";

// ── Helpers ──────────────────────────────────────────────────────────

function monthStr(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, "0")}`;
}

function monthLabel(year: number, month: number): string {
  const d = new Date(year, month - 1, 1);
  return d.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function getMonthGrid(year: number, month: number): (number | null)[][] {
  const firstDay = new Date(year, month - 1, 1);
  const startDow = (firstDay.getDay() + 6) % 7;
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
            ? "border-slate-700 bg-slate-900 hover:border-slate-600"
            : "border-slate-800/50 bg-slate-950/30 hover:border-slate-700"
        }`}
      >
        {/* Day number */}
        <div className="mb-0.5 flex items-center justify-between">
          <span
            className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-medium ${
              today
                ? "bg-emerald-700 text-white"
                : hasActivity
                  ? "text-slate-100"
                  : "text-slate-500"
            }`}
          >
            {day}
          </span>
        </div>

        {/* Climbing info */}
        {entry?.climbing && (
          <div className="flex items-center gap-1">
            <ActivityIcon category="climbing" size="xs" />
            <span
              className={`text-[10px] font-medium ${VENUE_COLORS[entry.climbing.venue_type] ?? "text-slate-400"}`}
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
                <span key={i}>
                  <ActivityIcon category={sportCategory(a.type)} size="xs" />
                </span>
              ))}
              {entry.endurance.activities.length > 3 && (
                <span className="text-[9px] text-slate-500">
                  +{entry.endurance.activities.length - 3}
                </span>
              )}
            </div>
          ) : (
            <div className="space-y-px">
              {entry.endurance.activities.map((a, i) => (
                <div key={i} className="flex items-center gap-1">
                  <ActivityIcon category={sportCategory(a.type)} size="xs" />
                  <span className="text-[10px] text-slate-400">
                    {formatDuration(a.duration_s)}
                  </span>
                </div>
              ))}
            </div>
          ))}

        {/* Rest day indicator */}
        {!hasActivity && (
          <div className="mt-auto text-[9px] text-slate-700">
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
              className={`block rounded-xl border p-3 transition-colors hover:border-slate-600 ${
                entry
                  ? "border-slate-700 bg-slate-900"
                  : "border-slate-800/50 bg-slate-950/30"
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
                    today
                      ? "bg-emerald-700 text-white"
                      : "text-slate-300"
                  }`}
                >
                  {day}
                </span>
                <span className="text-sm text-slate-400">
                  {label}
                </span>
              </div>

              {!entry && (
                <div className="mt-1.5 text-xs text-slate-500">
                  Rest day
                </div>
              )}

              {entry?.climbing && (
                <div className="mt-2 flex items-center gap-2">
                  <ActivityIcon category="climbing" size="sm" />
                  <span
                    className={`text-sm font-medium ${VENUE_COLORS[entry.climbing.venue_type] ?? ""}`}
                  >
                    {entry.climbing.route_count} route
                    {entry.climbing.route_count !== 1 ? "s" : ""}
                  </span>
                  {entry.climbing.hardest_grade && (
                    <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-xs text-slate-300">
                      hardest: {entry.climbing.hardest_grade}
                    </span>
                  )}
                  <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">
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
                      <ActivityIcon category={sportCategory(a.type)} size="sm" />
                      <span className="text-sm text-slate-300">
                        {a.type}
                      </span>
                      <span className="text-sm text-slate-400">
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
              className="rounded-md border border-slate-700 px-2 py-1 text-sm hover:bg-slate-800"
            >
              &larr;
            </button>
            <h2 className="min-w-[10rem] text-center text-lg font-semibold text-slate-100">
              {monthLabel(year, month)}
            </h2>
            <button
              onClick={nextMonth}
              className="rounded-md border border-slate-700 px-2 py-1 text-sm hover:bg-slate-800"
            >
              &rarr;
            </button>
            <button
              onClick={goToday}
              className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-400 hover:bg-slate-800"
            >
              Today
            </button>
          </div>

          <div className="flex gap-1 rounded-lg border border-slate-700 p-0.5">
            {(["month", "week"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                  view === v
                    ? "bg-emerald-700 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {v.charAt(0).toUpperCase() + v.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {loading && (
          <div className="flex h-64 items-center justify-center text-sm text-slate-400">
            Loading...
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-400">
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
                  className="text-center text-[10px] font-medium uppercase tracking-wider text-slate-500"
                >
                  {wd}
                </div>
              ))}
            </div>

            {view === "month" ? (
              <div className="grid grid-cols-7 gap-1">
                {grid.flat().map((day, i) => (
                  <div key={i}>{renderDayCell(day, true)}</div>
                ))}
              </div>
            ) : (
              <>
                {/* Week selector strip */}
                <div className="mb-2 flex gap-1">
                  {grid.map((_, i) => (
                    <button
                      key={i}
                      onClick={() => setWeekIndex(i)}
                      className={`flex-1 rounded-md py-1 text-[10px] font-medium transition-colors ${
                        weekIndex === i
                          ? "bg-emerald-700 text-white"
                          : "bg-slate-800 text-slate-400 hover:bg-slate-700"
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
