"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  api,
  WeeklyStats,
  ActivityType,
  ACTIVITY_TYPE_LABELS,
  ACTIVITY_TYPE_HEX,
  ACTIVITY_TYPE_COLORS,
  ImportResult,
} from "@/lib/api";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function isoMonday(date: Date): string {
  const d = new Date(date);
  const day = d.getDay(); // 0=Sun
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return d.toISOString().slice(0, 10);
}

function addDays(iso: string, n: number): string {
  const d = new Date(iso + "T00:00:00");
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

function fmtWeekRange(start: string, end: string): string {
  const s = new Date(start + "T00:00:00");
  const e = new Date(end + "T00:00:00");
  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  return `${s.toLocaleDateString("en-US", opts)} – ${e.toLocaleDateString("en-US", { ...opts, year: "numeric" })}`;
}

function fmtDayLabel(iso: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", { weekday: "short", day: "numeric" });
}

const ALL_TYPES = Object.keys(ACTIVITY_TYPE_LABELS) as ActivityType[];

// ─── Component ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const currentWeek = isoMonday(new Date());
  const [weekStart, setWeekStart] = useState<string>(currentWeek);
  const [stats, setStats] = useState<WeeklyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedDay, setExpandedDay] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const initialisedRef = useRef(false);

  const loadStats = useCallback(async (ws: string) => {
    setLoading(true);
    try {
      const data = await api.stats.weekly(ws);
      setStats(data);
      // On first load: if this week is empty, jump back to the last week with data
      if (!initialisedRef.current && data.total_activities === 0 && ws === currentWeek) {
        initialisedRef.current = true;
        setWeekStart(addDays(ws, -7));
        return;
      }
      initialisedRef.current = true;
    } catch (e) {
      console.error(e);
      initialisedRef.current = true;
    } finally {
      setLoading(false);
    }
  }, [currentWeek]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadStats(weekStart);
  }, [weekStart, loadStats]);

  const prevWeek = () => setWeekStart(addDays(weekStart, -7));
  const nextWeek = () => setWeekStart(addDays(weekStart, 7));
  const isCurrentWeek = weekStart === isoMonday(new Date());

  // Build recharts data: one entry per day
  const chartData = stats
    ? stats.by_day.map((day) => {
        const entry: Record<string, string | number> = { day: fmtDayLabel(day.date), _date: day.date };
        for (const act of day.activities) {
          const t = act.activity_type;
          entry[t] = ((entry[t] as number) || 0) + 1;
        }
        return entry;
      })
    : [];

  const activeTypes = stats
    ? (ALL_TYPES.filter((t) => Object.keys(stats.by_type).includes(t)) as ActivityType[])
    : [];

  async function handleImport() {
    setImporting(true);
    setImportResult(null);
    try {
      const result = await api.import.intervals(730);
      setImportResult(result);
      // Reload stats after import
      await loadStats(weekStart);
    } catch (e: unknown) {
      setImportResult({
        total_fetched: 0,
        imported: 0,
        skipped: 0,
        errors: [(e as Error).message || "Unknown error"],
      });
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-emerald-400 mb-1">Dashboard</h1>
          <p className="text-slate-400 text-sm">Your outdoor activity overview</p>
        </div>
        <Link
          href="/chat"
          className="px-4 py-2 bg-emerald-700 hover:bg-emerald-600 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + Log Activity
        </Link>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          label="Activities"
          value={stats?.total_activities ?? "—"}
          sub={stats ? (stats.week_start === currentWeek ? "this week" : fmtWeekRange(stats.week_start, stats.week_end)) : "…"}
          loading={loading}
        />
        <StatCard
          label="Hours"
          value={stats ? stats.total_hours.toFixed(1) : "—"}
          sub={stats ? (stats.week_start === currentWeek ? "this week" : fmtWeekRange(stats.week_start, stats.week_end)) : "…"}
          loading={loading}
        />
        <StatCard
          label="Elevation"
          value={stats ? `${stats.total_elevation_m.toLocaleString()} m` : "—"}
          sub={stats ? (stats.week_start === currentWeek ? "this week" : fmtWeekRange(stats.week_start, stats.week_end)) : "…"}
          loading={loading}
        />
      </div>

      {/* Weekly chart */}
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-6">
        {/* Week nav */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={prevWeek}
            className="px-3 py-1 text-sm text-slate-400 hover:text-white border border-slate-700 rounded-lg transition-colors"
          >
            ← Prev
          </button>
          <span className="text-slate-200 font-medium text-sm">
            {stats ? fmtWeekRange(stats.week_start, stats.week_end) : "Loading…"}
          </span>
          <button
            onClick={nextWeek}
            disabled={isCurrentWeek}
            className="px-3 py-1 text-sm text-slate-400 hover:text-white border border-slate-700 rounded-lg transition-colors disabled:opacity-30"
          >
            Next →
          </button>
        </div>

        {loading ? (
          <div className="h-48 flex items-center justify-center text-slate-500 text-sm">Loading…</div>
        ) : chartData.every((d) => Object.keys(d).filter((k) => k !== "day" && k !== "_date").length === 0) ? (
          <div className="h-48 flex items-center justify-center text-slate-500 text-sm">
            No activities this week.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="day" tick={{ fontSize: 12, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} allowDecimals={false} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Legend
                wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
                formatter={(value) => ACTIVITY_TYPE_LABELS[value as ActivityType] || value}
              />
              {activeTypes.map((t) => (
                <Bar
                  key={t}
                  dataKey={t}
                  stackId="a"
                  fill={ACTIVITY_TYPE_HEX[t]}
                  name={t}
                  radius={activeTypes.indexOf(t) === activeTypes.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}

        {/* Day accordion */}
        {stats && (
          <div className="mt-4 space-y-1">
            {stats.by_day.map((day) => {
              if (day.activities.length === 0) return null;
              const isOpen = expandedDay === day.date;
              return (
                <div key={day.date} className="border border-slate-700/50 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setExpandedDay(isOpen ? null : day.date)}
                    className="w-full flex items-center justify-between px-4 py-2 text-sm hover:bg-slate-800 transition-colors"
                  >
                    <span className="text-slate-300 font-medium">{fmtDayLabel(day.date)}</span>
                    <span className="text-slate-500">
                      {day.activities.length} activit{day.activities.length !== 1 ? "ies" : "y"}
                      <span className="ml-2">{isOpen ? "▲" : "▼"}</span>
                    </span>
                  </button>
                  {isOpen && (
                    <div className="border-t border-slate-700/50 divide-y divide-slate-700/30">
                      {day.activities.map((act) => (
                        <Link
                          key={act.id}
                          href={`/activities/${act.id}`}
                          className="flex items-center gap-3 px-4 py-3 hover:bg-slate-800 transition-colors"
                        >
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ACTIVITY_TYPE_COLORS[act.activity_type]}`}>
                            {ACTIVITY_TYPE_LABELS[act.activity_type]}
                          </span>
                          <span className="text-slate-200 text-sm">{act.title}</span>
                          {act.tags && act.tags.length > 0 && (
                            <span className="text-xs text-slate-500">{act.tags.join(", ")}</span>
                          )}
                          {act.duration_minutes && (
                            <span className="ml-auto text-xs text-slate-500">
                              {Math.floor(act.duration_minutes / 60)}h {act.duration_minutes % 60}m
                            </span>
                          )}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          href="/activities"
          className="block p-5 rounded-xl border border-slate-700 bg-slate-900/50 hover:bg-slate-900 transition-colors"
        >
          <div className="text-xl mb-1">📋</div>
          <h2 className="font-semibold text-slate-200 mb-1">All Activities</h2>
          <p className="text-xs text-slate-500">Browse and filter your full history</p>
        </Link>

        {/* Garmin import */}
        <div className="p-5 rounded-xl border border-slate-700 bg-slate-900/50">
          <div className="text-xl mb-1">🔄</div>
          <h2 className="font-semibold text-slate-200 mb-1">Import from Garmin</h2>
          <p className="text-xs text-slate-500 mb-3">Sync your Garmin activities via intervals.icu (last 2 years)</p>
          <button
            onClick={handleImport}
            disabled={importing}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-sm text-white rounded-lg transition-colors"
          >
            {importing ? "Importing…" : "Import Now"}
          </button>
          {importResult && (
            <div className="mt-3 text-xs">
              {importResult.errors.length > 0 ? (
                <span className="text-red-400">{importResult.errors[0]}</span>
              ) : importResult.imported === 0 ? (
                <span className="text-slate-400">
                  ✓ Already up to date · {importResult.skipped} activities synced
                </span>
              ) : (
                <span className="text-emerald-400">
                  ✓ {importResult.imported} new · {importResult.skipped} already synced
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
  loading,
}: {
  label: string;
  value: string | number;
  sub: string;
  loading: boolean;
}) {
  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-5">
      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-2xl font-bold text-slate-100 ${loading ? "animate-pulse" : ""}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-0.5">{sub}</p>
    </div>
  );
}
