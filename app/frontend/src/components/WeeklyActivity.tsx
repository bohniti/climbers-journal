"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { fetchWeekly, type WeeklyData, type WeeklyDayEntry } from "@/lib/api";
import {
  CATEGORY_COLORS,
  TICK_COLORS,
  tickTypeLabel,
  formatDuration,
  sportCategory,
  type SportCategory,
} from "@/lib/constants";
import ActivityIcon from "@/components/ActivityIcon";

// ── Week Navigator ──────────────────────────────────────────────────

function WeekNavigator({
  weekStart,
  onPrev,
  onNext,
}: {
  weekStart: string;
  onPrev: () => void;
  onNext: () => void;
}) {
  const monday = new Date(weekStart + "T00:00:00");
  const sunday = new Date(monday);
  sunday.setDate(sunday.getDate() + 6);

  const fmt = (d: Date) =>
    d.toLocaleDateString(undefined, { month: "short", day: "numeric" });

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={onPrev}
        className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
      >
        ◀
      </button>
      <span className="text-xs text-slate-400">
        {fmt(monday)} – {fmt(sunday)}
      </span>
      <button
        onClick={onNext}
        className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
      >
        ▶
      </button>
    </div>
  );
}

// ── Day Accordion ───────────────────────────────────────────────────

function DayAccordion({ day }: { day: WeeklyDayEntry }) {
  const [open, setOpen] = useState(false);
  const d = new Date(day.date + "T00:00:00");
  const label = d.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const totalItems = day.climbing_count + day.endurance_activities.length;

  if (totalItems === 0) {
    return (
      <div className="flex items-center justify-between rounded-lg px-3 py-2 text-sm text-slate-500">
        <span>{label}</span>
        <span className="text-xs">Rest day</span>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-800">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-2 text-sm text-slate-200 hover:bg-slate-800/50"
      >
        <span>{label}</span>
        <span className="flex items-center gap-2 text-xs text-slate-400">
          {day.climbing_count > 0 && (
            <span>{day.climbing_count} climb{day.climbing_count !== 1 ? "s" : ""}</span>
          )}
          {day.endurance_activities.length > 0 && (
            <span>
              {day.endurance_activities.length} activit
              {day.endurance_activities.length !== 1 ? "ies" : "y"}
            </span>
          )}
          <span>{open ? "▲" : "▼"}</span>
        </span>
      </button>
      {open && (
        <div className="space-y-1 border-t border-slate-800 px-3 py-2">
          {day.ascents.map((a, i) => (
            <div key={`a-${i}`} className="flex items-center gap-2 text-xs">
              <ActivityIcon category="climbing" size="sm" />
              <span className="text-slate-200">
                {a.route_name ?? "Unnamed"}
              </span>
              {a.grade && (
                <span className="font-mono text-slate-400">{a.grade}</span>
              )}
              <span
                className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                  TICK_COLORS[a.tick_type] ?? TICK_COLORS.attempt
                }`}
              >
                {tickTypeLabel(a.tick_type)}
              </span>
            </div>
          ))}
          {day.endurance_activities.map((e, i) => (
            <div key={`e-${i}`} className="flex items-center gap-2 text-xs">
              <ActivityIcon category={sportCategory(e.type)} size="sm" />
              <span className="text-slate-200">{e.name ?? e.type}</span>
              <span className="text-slate-400">
                {formatDuration(e.duration_s)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Chart Tooltip ───────────────────────────────────────────────────

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs shadow-lg">
      <div className="mb-1 font-medium text-slate-200">{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span
            className="inline-block h-2 w-2 rounded-sm"
            style={{ backgroundColor: p.fill }}
          />
          <span className="text-slate-300">
            {CATEGORY_COLORS[p.dataKey as SportCategory]?.label ?? p.dataKey}:
          </span>
          <span className="text-slate-100">{p.value}</span>
        </div>
      ))}
    </div>
  );
}

// ── Main Component ──────────────────────────────────────────────────

function getMonday(d: Date): Date {
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  return new Date(d.getFullYear(), d.getMonth(), diff);
}

function toISO(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const CHART_CATEGORIES: SportCategory[] = [
  "climbing", "run", "ride", "swim", "winter", "water", "fitness", "other",
];

export default function WeeklyActivity() {
  const [weekStart, setWeekStart] = useState(() => toISO(getMonday(new Date())));
  const [data, setData] = useState<WeeklyData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await fetchWeekly(weekStart);
      setData(d);
    } catch {
      // Silently fail — dashboard shows other data
    } finally {
      setLoading(false);
    }
  }, [weekStart]);

  useEffect(() => {
    load();
  }, [load]);

  const navigateWeek = (delta: number) => {
    const d = new Date(weekStart + "T00:00:00");
    d.setDate(d.getDate() + delta * 7);
    setWeekStart(toISO(d));
  };

  // Build chart data — count activities by category per day
  const chartData = data?.days.map((day) => {
    const d = new Date(day.date + "T00:00:00");
    const dayLabel = d.toLocaleDateString(undefined, { weekday: "short" });

    const counts: Record<string, number> = {};

    // Count climbing ascents
    if (day.climbing_count > 0) {
      counts["climbing"] = day.climbing_count;
    }

    // Count endurance by sport category
    for (const e of day.endurance_activities) {
      const category = sportCategory(e.type);
      counts[category] = (counts[category] || 0) + 1;
    }

    return { name: dayLabel, ...counts };
  }) ?? [];

  // Determine which categories are present this week
  const activeCategories = new Set<string>();
  for (const d of chartData) {
    for (const key of Object.keys(d)) {
      if (key !== "name" && (d as any)[key] > 0) activeCategories.add(key);
    }
  }

  return (
    <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-medium uppercase tracking-wider text-slate-400">
          Weekly Activity
        </h3>
        <WeekNavigator
          weekStart={weekStart}
          onPrev={() => navigateWeek(-1)}
          onNext={() => navigateWeek(1)}
        />
      </div>

      {/* Session streak */}
      {data && data.session_streak > 0 && (
        <div className="mb-3 text-xs text-slate-400">
          <span className="text-orange-400 font-semibold">&#x25CF;</span> {data.session_streak} climbing session
          {data.session_streak !== 1 ? "s" : ""} this month
        </div>
      )}

      {loading ? (
        <div className="flex h-[220px] items-center justify-center text-sm text-slate-500">
          Loading...
        </div>
      ) : (
        <>
          {/* Legend */}
          <div className="mb-2 flex flex-wrap gap-3 text-[10px]">
            {CHART_CATEGORIES
              .filter((cat) => activeCategories.has(cat))
              .map((cat) => (
                <div key={cat} className="flex items-center gap-1">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-sm"
                    style={{ backgroundColor: CATEGORY_COLORS[cat].hex }}
                  />
                  <span className="text-slate-400">{CATEGORY_COLORS[cat].label}</span>
                </div>
              ))}
          </div>

          {/* Chart */}
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} barCategoryGap="20%">
              <XAxis
                dataKey="name"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip content={<ChartTooltip />} cursor={false} />
              {CHART_CATEGORIES.map((cat) => (
                <Bar
                  key={cat}
                  dataKey={cat}
                  stackId="a"
                  fill={CATEGORY_COLORS[cat].hex}
                  radius={[0, 0, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>

          {/* Day accordion */}
          {data && (
            <div className="mt-3 space-y-1">
              {data.days.map((day) => (
                <DayAccordion key={day.date} day={day} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
