"use client";

import { useState } from "react";
import { updateSession, type FeedSessionData } from "@/lib/api";
import CragCombobox from "@/components/CragCombobox";

interface SessionEditModalProps {
  session: FeedSessionData;
  onClose: () => void;
  onSaved: () => void;
}

export default function SessionEditModal({
  session,
  onClose,
  onSaved,
}: SessionEditModalProps) {
  const [notes, setNotes] = useState(session.notes ?? "");
  const [newCragId, setNewCragId] = useState<number | null>(null);
  const [newCragName, setNewCragName] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmCrag, setConfirmCrag] = useState(false);

  const cragChanged = newCragId != null && newCragId !== session.crag_id;

  const handleSave = async () => {
    // If crag changed and not yet confirmed, show confirmation
    if (cragChanged && !confirmCrag) {
      setConfirmCrag(true);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const data: Record<string, unknown> = {};
      if (cragChanged) data.crag_id = newCragId;
      if (notes !== (session.notes ?? "")) data.notes = notes || null;

      if (Object.keys(data).length > 0) {
        await updateSession(session.id, data);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
      setConfirmCrag(false);
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
        <h3 className="text-sm font-medium text-slate-100">Edit session</h3>
        <p className="mt-0.5 text-xs text-slate-500">
          {session.crag_name} &middot; {session.date}
        </p>

        {error && (
          <div className="mt-3 rounded-lg border border-red-800 bg-red-950/40 px-3 py-2 text-xs text-red-400">
            {error}
          </div>
        )}

        {/* Crag picker */}
        <div className="mt-4">
          <label className="mb-1 block text-xs font-medium text-slate-400">
            Crag
          </label>
          <CragCombobox
            value={newCragId ?? session.crag_id}
            onChange={(id, name) => {
              setNewCragId(id);
              setNewCragName(name);
              setConfirmCrag(false);
            }}
          />
        </div>

        {/* Crag change confirmation */}
        {confirmCrag && cragChanged && (
          <div className="mt-2 rounded-lg border border-amber-800 bg-amber-950/40 px-3 py-2 text-xs text-amber-300">
            Move {session.ascent_count} route
            {session.ascent_count !== 1 ? "s" : ""} to{" "}
            <span className="font-medium">{newCragName}</span>?
          </div>
        )}

        {/* Notes */}
        <div className="mt-4">
          <label className="mb-1 block text-xs font-medium text-slate-400">
            Notes
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:ring-2 focus:ring-emerald-600 outline-none"
            placeholder="Session notes..."
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
            {saving
              ? "Saving..."
              : confirmCrag
                ? "Confirm move"
                : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
