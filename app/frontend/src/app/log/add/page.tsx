"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  createClimbingSession,
  listCrags,
  type CragResponse,
  type ClimbingSessionResponse,
} from "@/lib/api";

// ── Constants ────────────────────────────────────────────────────────

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

const VENUE_TYPES = [
  { value: "outdoor_crag", label: "Outdoor crag" },
  { value: "indoor_gym", label: "Indoor gym" },
] as const;

const GRADE_SYSTEMS = [
  { value: "french", label: "French (8a, 7b+)" },
  { value: "yds", label: "YDS (5.12a)" },
  { value: "v_scale", label: "V-scale (V10)" },
  { value: "uiaa", label: "UIAA (IX-)" },
  { value: "font", label: "Font (6a+)" },
] as const;

const STORAGE_KEY = "climbers-journal-add-draft";

// ── Shared input class ──────────────────────────────────────────────

const inputClass =
  "w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:ring-2 focus:ring-emerald-600 outline-none";

// ── Types ────────────────────────────────────────────────────────────

interface AscentDraft {
  route_name: string;
  grade: string;
  tick_type: string;
  style: string;
  tries: string;
  rating: string;
  notes: string;
  partner: string;
}

interface FormState {
  crag_name: string;
  crag_country: string;
  crag_region: string;
  venue_type: string;
  grade_system: string;
  date: string;
  ascents: AscentDraft[];
}

function emptyAscent(): AscentDraft {
  return {
    route_name: "",
    grade: "",
    tick_type: "redpoint",
    style: "sport",
    tries: "",
    rating: "",
    notes: "",
    partner: "",
  };
}

function defaultForm(): FormState {
  return {
    crag_name: "",
    crag_country: "",
    crag_region: "",
    venue_type: "outdoor_crag",
    grade_system: "french",
    date: new Date().toISOString().slice(0, 10),
    ascents: [emptyAscent()],
  };
}

// ── Component ────────────────────────────────────────────────────────

export default function AddSessionPage() {
  const [form, setForm] = useState<FormState>(defaultForm);
  const [crags, setCrags] = useState<CragResponse[]>([]);
  const [cragSearch, setCragSearch] = useState("");
  const [showCragDropdown, setShowCragDropdown] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ClimbingSessionResponse | null>(null);
  const cragInputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const isGym = form.venue_type === "indoor_gym";

  useEffect(() => {
    listCrags({ limit: 200 }).then(setCrags).catch(() => {});
  }, []);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as FormState;
        if (parsed.ascents?.length > 0) {
          setForm(parsed);
          setCragSearch(parsed.crag_name);
        }
      }
    } catch {
      // ignore corrupted storage
    }
  }, []);

  useEffect(() => {
    if (!result) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(form));
    }
  }, [form, result]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        cragInputRef.current &&
        !cragInputRef.current.contains(e.target as Node)
      ) {
        setShowCragDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const filteredCrags = useMemo(() => {
    if (!cragSearch.trim()) return crags;
    const q = cragSearch.toLowerCase();
    return crags.filter((c) => c.name.toLowerCase().includes(q));
  }, [crags, cragSearch]);

  const selectCrag = useCallback(
    (crag: CragResponse) => {
      setForm((prev) => ({
        ...prev,
        crag_name: crag.name,
        crag_country: crag.country ?? "",
        crag_region: crag.region ?? "",
        venue_type: crag.venue_type,
        grade_system: crag.default_grade_sys,
      }));
      setCragSearch(crag.name);
      setShowCragDropdown(false);
    },
    []
  );

  const updateAscent = useCallback(
    (index: number, updates: Partial<AscentDraft>) => {
      setForm((prev) => ({
        ...prev,
        ascents: prev.ascents.map((a, i) =>
          i === index ? { ...a, ...updates } : a
        ),
      }));
    },
    []
  );

  const removeAscent = useCallback((index: number) => {
    setForm((prev) => ({
      ...prev,
      ascents: prev.ascents.filter((_, i) => i !== index),
    }));
  }, []);

  const addAscent = useCallback(() => {
    setForm((prev) => ({
      ...prev,
      ascents: [...prev.ascents, emptyAscent()],
    }));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!form.crag_name.trim()) {
      setError("Crag name is required");
      return;
    }
    if (form.ascents.length === 0) {
      setError("Add at least one ascent");
      return;
    }
    if (!isGym) {
      const missing = form.ascents.findIndex((a) => !a.route_name.trim());
      if (missing >= 0) {
        setError(`Ascent ${missing + 1}: route name is required for outdoor crags`);
        return;
      }
    }

    setSaving(true);
    setError(null);

    try {
      const res = await createClimbingSession({
        crag_name: form.crag_name.trim(),
        crag_country: form.crag_country.trim() || null,
        crag_region: form.crag_region.trim() || null,
        venue_type: form.venue_type,
        default_grade_sys: form.grade_system,
        ascents: form.ascents.map((a) => ({
          route_name: a.route_name.trim() || null,
          grade: a.grade.trim() || null,
          tick_type: a.tick_type,
          date: form.date,
          tries: a.tries ? parseInt(a.tries) : null,
          rating: a.rating ? parseInt(a.rating) : null,
          notes: a.notes.trim() || null,
          partner: a.partner.trim() || null,
          style: a.style || null,
        })),
      });
      setResult(res);
      localStorage.removeItem(STORAGE_KEY);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save session");
    } finally {
      setSaving(false);
    }
  }, [form, isGym]);

  const handleNewSession = useCallback(() => {
    setForm(defaultForm());
    setCragSearch("");
    setResult(null);
    setError(null);
  }, []);

  // ── Success state ──────────────────────────────────────────────────

  if (result) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="mx-4 max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 text-center">
          <div className="mb-3 text-3xl">&#x2705;</div>
          <h2 className="mb-1 text-lg font-semibold text-slate-100">
            Session saved
          </h2>
          <p className="mb-4 text-sm text-slate-400">
            {result.ascents_created} ascent(s) at {result.crag_name}
            {result.crag_created && " (new crag)"}
            {result.ascents_skipped > 0 &&
              ` \u00b7 ${result.ascents_skipped} duplicate(s) skipped`}
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={handleNewSession}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
            >
              Log another
            </button>
            <Link
              href="/log"
              className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600"
            >
              View log
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ── Form ───────────────────────────────────────────────────────────

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-2xl px-4 py-6">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-lg font-semibold text-slate-100">
            Log climbing session
          </h1>
          <Link
            href="/log"
            className="text-sm text-slate-400 hover:text-slate-200"
          >
            Cancel
          </Link>
        </div>

        {/* ── Crag section ─────────────────────────────────────── */}
        <section className="mb-6 rounded-xl border border-slate-700 bg-slate-900 p-4">
          <h2 className="mb-3 text-sm font-medium text-slate-100">
            Crag
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {/* Crag name with autocomplete */}
            <div className="relative sm:col-span-2">
              <label className="mb-1 block text-xs text-slate-400">
                Name
              </label>
              <input
                ref={cragInputRef}
                type="text"
                value={cragSearch}
                onChange={(e) => {
                  setCragSearch(e.target.value);
                  setForm((prev) => ({
                    ...prev,
                    crag_name: e.target.value,
                  }));
                  setShowCragDropdown(true);
                }}
                onFocus={() => setShowCragDropdown(true)}
                placeholder="Search or enter crag name"
                className={inputClass}
              />
              {showCragDropdown && filteredCrags.length > 0 && (
                <div
                  ref={dropdownRef}
                  className="absolute left-0 right-0 top-full z-10 mt-1 max-h-48 overflow-y-auto rounded-lg border border-slate-700 bg-slate-900 shadow-lg"
                >
                  {filteredCrags.slice(0, 20).map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => selectCrag(c)}
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-800"
                    >
                      <span className="text-slate-100">
                        {c.name}
                      </span>
                      {c.country && (
                        <span className="text-xs text-slate-400">
                          {c.country}
                        </span>
                      )}
                      <span className="ml-auto rounded-full bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                        {c.venue_type === "indoor_gym" ? "gym" : "outdoor"}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Venue type */}
            <div>
              <label className="mb-1 block text-xs text-slate-400">
                Venue type
              </label>
              <select
                value={form.venue_type}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    venue_type: e.target.value,
                  }))
                }
                className={inputClass}
              >
                {VENUE_TYPES.map((v) => (
                  <option key={v.value} value={v.value}>
                    {v.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Grade system */}
            <div>
              <label className="mb-1 block text-xs text-slate-400">
                Grade system
              </label>
              <select
                value={form.grade_system}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    grade_system: e.target.value,
                  }))
                }
                className={inputClass}
              >
                {GRADE_SYSTEMS.map((g) => (
                  <option key={g.value} value={g.value}>
                    {g.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Country */}
            <div>
              <label className="mb-1 block text-xs text-slate-400">
                Country
              </label>
              <input
                type="text"
                value={form.crag_country}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    crag_country: e.target.value,
                  }))
                }
                placeholder="e.g. Germany"
                className={inputClass}
              />
            </div>

            {/* Region */}
            <div>
              <label className="mb-1 block text-xs text-slate-400">
                Region
              </label>
              <input
                type="text"
                value={form.crag_region}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    crag_region: e.target.value,
                  }))
                }
                placeholder="e.g. Frankenjura"
                className={inputClass}
              />
            </div>
          </div>
        </section>

        {/* ── Date section ─────────────────────────────────────── */}
        <section className="mb-6 rounded-xl border border-slate-700 bg-slate-900 p-4">
          <div className="flex items-center gap-4">
            <div>
              <label className="mb-1 block text-xs text-slate-400">
                Date
              </label>
              <input
                type="date"
                value={form.date}
                max={new Date().toISOString().slice(0, 10)}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, date: e.target.value }))
                }
                className={inputClass}
              />
            </div>
          </div>
        </section>

        {/* ── Ascents section ──────────────────────────────────── */}
        <section className="mb-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium text-slate-100">
              Ascents ({form.ascents.length})
            </h2>
            <button
              type="button"
              onClick={addAscent}
              className="rounded-lg border border-slate-700 px-3 py-1 text-xs text-slate-400 hover:bg-slate-800"
            >
              + Add ascent
            </button>
          </div>

          <div className="space-y-3">
            {form.ascents.map((a, i) => (
              <div
                key={i}
                className="rounded-xl border border-slate-700 bg-slate-900 p-4"
              >
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-500">
                    #{i + 1}
                  </span>
                  {form.ascents.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeAscent(i)}
                      className="text-xs text-slate-400 hover:text-red-400"
                    >
                      Remove
                    </button>
                  )}
                </div>

                {/* Row 1: Route + Grade */}
                <div className="mb-2 grid grid-cols-[1fr_100px] gap-2">
                  <div>
                    <label className="mb-1 block text-xs text-slate-400">
                      {isGym ? "Route (optional)" : "Route"}
                    </label>
                    <input
                      type="text"
                      value={a.route_name}
                      onChange={(e) =>
                        updateAscent(i, { route_name: e.target.value })
                      }
                      placeholder={isGym ? "Optional" : "Route name"}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-slate-400">
                      Grade
                    </label>
                    <input
                      type="text"
                      value={a.grade}
                      onChange={(e) =>
                        updateAscent(i, { grade: e.target.value })
                      }
                      placeholder="e.g. 8a"
                      className={inputClass}
                    />
                  </div>
                </div>

                {/* Row 2: Tick type + Style + Tries */}
                <div className="mb-2 grid grid-cols-3 gap-2">
                  <div>
                    <label className="mb-1 block text-xs text-slate-400">
                      Tick type
                    </label>
                    <select
                      value={a.tick_type}
                      onChange={(e) =>
                        updateAscent(i, { tick_type: e.target.value })
                      }
                      className={inputClass}
                    >
                      {TICK_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t.charAt(0).toUpperCase() + t.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-slate-400">
                      Style
                    </label>
                    <select
                      value={a.style}
                      onChange={(e) =>
                        updateAscent(i, { style: e.target.value })
                      }
                      className={inputClass}
                    >
                      {STYLES.map((s) => (
                        <option key={s} value={s}>
                          {s.replace("_", " ")}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-slate-400">
                      Tries
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={a.tries}
                      onChange={(e) =>
                        updateAscent(i, { tries: e.target.value })
                      }
                      placeholder="1"
                      className={inputClass}
                    />
                  </div>
                </div>

                {/* Row 3: Rating + Partner */}
                <div className="mb-2 grid grid-cols-2 gap-2">
                  <div>
                    <label className="mb-1 block text-xs text-slate-400">
                      Rating
                    </label>
                    <select
                      value={a.rating}
                      onChange={(e) =>
                        updateAscent(i, { rating: e.target.value })
                      }
                      className={inputClass}
                    >
                      <option value="">No rating</option>
                      <option value="1">1 star</option>
                      <option value="2">2 stars</option>
                      <option value="3">3 stars</option>
                      <option value="4">4 stars</option>
                      <option value="5">5 stars</option>
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-slate-400">
                      Partner
                    </label>
                    <input
                      type="text"
                      value={a.partner}
                      onChange={(e) =>
                        updateAscent(i, { partner: e.target.value })
                      }
                      placeholder="Optional"
                      className={inputClass}
                    />
                  </div>
                </div>

                {/* Row 4: Notes */}
                <div>
                  <label className="mb-1 block text-xs text-slate-400">
                    Notes
                  </label>
                  <textarea
                    value={a.notes}
                    onChange={(e) =>
                      updateAscent(i, { notes: e.target.value })
                    }
                    placeholder="Optional notes"
                    rows={2}
                    className="w-full resize-none rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 outline-none focus:ring-2 focus:ring-emerald-600"
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Add ascent (bottom) */}
          <button
            type="button"
            onClick={addAscent}
            className="mt-3 w-full rounded-xl border border-dashed border-slate-700 py-2.5 text-sm text-slate-400 hover:border-slate-600"
          >
            + Add another ascent
          </button>
        </section>

        {/* ── Error ────────────────────────────────────────────── */}
        {error && (
          <div className="mb-4 rounded-lg border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* ── Submit ───────────────────────────────────────────── */}
        <div className="flex justify-end gap-3 pb-8">
          <Link
            href="/log"
            className="rounded-lg px-4 py-2 text-sm text-slate-400 hover:bg-slate-800"
          >
            Cancel
          </Link>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={saving}
            className="rounded-lg bg-emerald-700 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-40"
          >
            {saving ? "Saving..." : "Save session"}
          </button>
        </div>
      </div>
    </div>
  );
}
