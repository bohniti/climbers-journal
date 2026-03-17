"use client";

import { useState } from "react";
import { updateActivity, type ActivityResponse } from "@/lib/api";

interface EnduranceEditModalProps {
  activity: ActivityResponse;
  onClose: () => void;
  onSaved: () => void;
}

export default function EnduranceEditModal({
  activity,
  onClose,
  onSaved,
}: EnduranceEditModalProps) {
  const [name, setName] = useState(activity.name ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      const data: Record<string, unknown> = {};
      if (name !== (activity.name ?? "")) data.name = name || null;

      if (Object.keys(data).length > 0) {
        await updateActivity(activity.id, data);
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
        <h3 className="text-sm font-medium text-slate-100">Edit activity</h3>
        <p className="mt-0.5 text-xs text-slate-500">
          {activity.type} &middot; {activity.date}
        </p>

        {error && (
          <div className="mt-3 rounded-lg border border-red-800 bg-red-950/40 px-3 py-2 text-xs text-red-400">
            {error}
          </div>
        )}

        {/* Name */}
        <div className="mt-4">
          <label className="mb-1 block text-xs font-medium text-slate-400">
            Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:ring-2 focus:ring-emerald-600 outline-none"
            placeholder="Activity name..."
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
