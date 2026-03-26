"use client";

import { useState } from "react";
import { updateAscent, type ActivityAscent } from "@/lib/api";
import { tickTypeLabel } from "@/lib/constants";

const TICK_TYPES = [
  "onsight",
  "flash",
  "redpoint",
  "pinkpoint",
  "repeat",
  "attempt",
  "hang",
];

interface AscentEditModalProps {
  ascent: ActivityAscent;
  onClose: () => void;
  onSaved: () => void;
}

export default function AscentEditModal({
  ascent,
  onClose,
  onSaved,
}: AscentEditModalProps) {
  const [grade, setGrade] = useState(ascent.grade ?? "");
  const [tickType, setTickType] = useState(ascent.tick_type);
  const [tries, setTries] = useState(ascent.tries?.toString() ?? "");
  const [rating, setRating] = useState(ascent.rating?.toString() ?? "");
  const [notes, setNotes] = useState(ascent.notes ?? "");
  const [partner, setPartner] = useState(ascent.partner ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inputClass =
    "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:ring-2 focus:ring-emerald-600 outline-none";

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      const data: Record<string, unknown> = {};

      if (grade !== (ascent.grade ?? "")) data.grade = grade || null;
      if (tickType !== ascent.tick_type) data.tick_type = tickType;
      if (tries !== (ascent.tries?.toString() ?? ""))
        data.tries = tries ? parseInt(tries, 10) : null;
      if (rating !== (ascent.rating?.toString() ?? ""))
        data.rating = rating ? parseInt(rating, 10) : null;
      if (notes !== (ascent.notes ?? "")) data.notes = notes || null;
      if (partner !== (ascent.partner ?? "")) data.partner = partner || null;

      if (Object.keys(data).length > 0) {
        await updateAscent(ascent.id, data);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="mx-4 w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-5">
        <h3 className="text-sm font-medium text-slate-100">Edit ascent</h3>
        <p className="mt-0.5 text-xs text-slate-500">
          {ascent.route_name ?? "Unnamed route"}
          {ascent.grade ? ` · ${ascent.grade}` : ""}
        </p>

        {error && (
          <div className="mt-3 rounded-lg border border-red-800 bg-red-950/40 px-3 py-2 text-xs text-red-400">
            {error}
          </div>
        )}

        <div className="mt-4 grid grid-cols-2 gap-3">
          {/* Grade */}
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">
              Grade
            </label>
            <input
              type="text"
              value={grade}
              onChange={(e) => setGrade(e.target.value)}
              className={inputClass}
              placeholder="e.g. 6a+"
            />
          </div>

          {/* Tick type */}
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">
              Tick type
            </label>
            <select
              value={tickType}
              onChange={(e) => setTickType(e.target.value)}
              className={inputClass}
            >
              {TICK_TYPES.map((tt) => (
                <option key={tt} value={tt}>
                  {tickTypeLabel(tt)}
                </option>
              ))}
            </select>
          </div>

          {/* Tries */}
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">
              Tries
            </label>
            <input
              type="number"
              min={1}
              value={tries}
              onChange={(e) => setTries(e.target.value)}
              className={inputClass}
              placeholder="1"
            />
          </div>

          {/* Rating */}
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">
              Rating (1-5)
            </label>
            <input
              type="number"
              min={1}
              max={5}
              value={rating}
              onChange={(e) => setRating(e.target.value)}
              className={inputClass}
              placeholder="1-5"
            />
          </div>
        </div>

        {/* Partner */}
        <div className="mt-3">
          <label className="mb-1 block text-xs font-medium text-slate-400">
            Partner
          </label>
          <input
            type="text"
            value={partner}
            onChange={(e) => setPartner(e.target.value)}
            className={inputClass}
            placeholder="Climbing partner"
          />
        </div>

        {/* Notes */}
        <div className="mt-3">
          <label className="mb-1 block text-xs font-medium text-slate-400">
            Notes
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className={inputClass}
            placeholder="Route notes..."
          />
        </div>

        {/* Actions */}
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="rounded-lg bg-emerald-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
