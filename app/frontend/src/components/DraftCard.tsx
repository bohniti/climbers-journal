"use client";

import { useCallback, useState } from "react";
import type { DraftCard, DraftAscent } from "@/lib/api";
import { createClimbingSession } from "@/lib/api";

const TICK_TYPES = [
  "onsight",
  "flash",
  "redpoint",
  "pinkpoint",
  "repeat",
  "attempt",
  "hang",
] as const;

const STYLES = ["sport", "trad", "boulder", "multi_pitch", "alpine"] as const;

const inputClass =
  "rounded border border-slate-700 bg-slate-800 px-2 py-1 text-sm text-slate-100 outline-none focus:ring-2 focus:ring-emerald-600";

interface DraftCardProps {
  draft: DraftCard;
  onConfirmed: (message: string) => void;
  onCancelled: () => void;
}

export default function DraftCardView({
  draft,
  onConfirmed,
  onCancelled,
}: DraftCardProps) {
  const [cragName, setCragName] = useState(draft.crag.name);
  const [sessionDate, setSessionDate] = useState(
    draft.date ?? new Date().toISOString().slice(0, 10)
  );
  const [ascents, setAscents] = useState<DraftAscent[]>(draft.ascents);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateAscent = useCallback(
    (index: number, updates: Partial<DraftAscent>) => {
      setAscents((prev) =>
        prev.map((a, i) => (i === index ? { ...a, ...updates } : a))
      );
    },
    []
  );

  const removeAscent = useCallback((index: number) => {
    setAscents((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const addAscent = useCallback(() => {
    setAscents((prev) => [
      ...prev,
      { tick_type: "redpoint", style: "sport" },
    ]);
  }, []);

  const handleConfirm = useCallback(async () => {
    if (ascents.length === 0) return;
    setSaving(true);
    setError(null);

    try {
      const result = await createClimbingSession({
        crag_name: cragName,
        crag_country: draft.crag.country,
        venue_type: draft.crag.venue_type,
        default_grade_sys: draft.crag.grade_system,
        ascents: ascents.map((a) => ({
          route_name: a.route_name || null,
          grade: a.grade || null,
          tick_type: a.tick_type,
          date: sessionDate,
          tries: a.tries ?? null,
          notes: a.notes || null,
          style: a.style || null,
        })),
      });

      const msg =
        `Saved ${result.ascents_created} ascent(s) at ${result.crag_name}` +
        (result.ascents_skipped > 0
          ? ` (${result.ascents_skipped} duplicate(s) skipped)`
          : "");
      onConfirmed(msg);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }, [ascents, cragName, sessionDate, draft.crag, onConfirmed]);

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 p-4">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-100">
          Draft: Climbing Session
        </h3>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            draft.crag.status === "existing"
              ? "bg-green-900/40 text-green-300"
              : "bg-blue-900/40 text-blue-300"
          }`}
        >
          {draft.crag.status === "existing" ? "Known crag" : "New crag"}
        </span>
      </div>

      {/* Crag + Date */}
      <div className="mb-3 grid grid-cols-2 gap-2">
        <div>
          <label className="mb-1 block text-xs text-slate-400">
            Crag
          </label>
          <input
            type="text"
            value={cragName}
            onChange={(e) => setCragName(e.target.value)}
            className={`w-full ${inputClass}`}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-400">
            Date
          </label>
          <input
            type="date"
            value={sessionDate}
            onChange={(e) => setSessionDate(e.target.value)}
            className={`w-full ${inputClass}`}
          />
        </div>
      </div>

      {/* Ascents */}
      <div className="mb-3 space-y-2">
        <label className="block text-xs text-slate-400">
          Ascents
        </label>
        {ascents.map((a, i) => (
          <div
            key={i}
            className="rounded-lg border border-slate-700 bg-slate-800 p-2.5"
          >
            <div className="mb-2 flex items-center gap-2">
              <input
                type="text"
                placeholder="Route name"
                value={a.route_name ?? ""}
                onChange={(e) =>
                  updateAscent(i, { route_name: e.target.value || undefined })
                }
                className={`flex-1 ${inputClass}`}
              />
              {a.route_status && (
                <span
                  className={`shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                    a.route_status === "existing"
                      ? "bg-green-900/40 text-green-300"
                      : "bg-blue-900/40 text-blue-300"
                  }`}
                >
                  {a.route_status}
                </span>
              )}
              <button
                type="button"
                onClick={() => removeAscent(i)}
                className="shrink-0 text-slate-400 hover:text-red-400"
                title="Remove ascent"
              >
                &times;
              </button>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Grade"
                value={a.grade ?? ""}
                onChange={(e) =>
                  updateAscent(i, { grade: e.target.value || undefined })
                }
                className={`w-20 ${inputClass}`}
              />
              <select
                value={a.tick_type}
                onChange={(e) => updateAscent(i, { tick_type: e.target.value })}
                className={inputClass}
              >
                {TICK_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <select
                value={a.style ?? "sport"}
                onChange={(e) => updateAscent(i, { style: e.target.value })}
                className={inputClass}
              >
                {STYLES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              <input
                type="number"
                placeholder="Tries"
                min={1}
                value={a.tries ?? ""}
                onChange={(e) =>
                  updateAscent(i, {
                    tries: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
                className={`w-16 ${inputClass}`}
              />
            </div>
          </div>
        ))}
        <button
          type="button"
          onClick={addAscent}
          className="w-full rounded-lg border border-dashed border-slate-700 py-1.5 text-xs text-slate-400 hover:border-slate-600"
        >
          + Add ascent
        </button>
      </div>

      {/* Error */}
      {error && (
        <p className="mb-2 text-xs text-red-400">{error}</p>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancelled}
          disabled={saving}
          className="rounded-lg px-3 py-1.5 text-sm text-slate-400 hover:bg-slate-800"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={saving || ascents.length === 0}
          className="rounded-lg bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-40"
        >
          {saving ? "Saving..." : "Confirm"}
        </button>
      </div>
    </div>
  );
}
