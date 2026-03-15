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

  // Load crags for autocomplete
  useEffect(() => {
    listCrags({ limit: 200 }).then(setCrags).catch(() => {});
  }, []);

  // Load draft from localStorage on mount
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

  // Auto-save draft to localStorage
  useEffect(() => {
    if (!result) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(form));
    }
  }, [form, result]);

  // Close dropdown on outside click
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

  // Filtered crags for dropdown
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
    // For outdoor crags, route name is required
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
        <div className="mx-4 max-w-md rounded-xl border border-zinc-200 bg-white p-6 text-center dark:border-zinc-800 dark:bg-zinc-900">
          <div className="mb-3 text-3xl">&#x2705;</div>
          <h2 className="mb-1 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            Session saved
          </h2>
          <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
            {result.ascents_created} ascent(s) at {result.crag_name}
            {result.crag_created && " (new crag)"}
            {result.ascents_skipped > 0 &&
              ` \u00b7 ${result.ascents_skipped} duplicate(s) skipped`}
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={handleNewSession}
              className="rounded-lg border border-zinc-300 px-4 py-2 text-sm text-zinc-700 hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800"
            >
              Log another
            </button>
            <Link
              href="/log"
              className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
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
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            Log climbing session
          </h1>
          <Link
            href="/log"
            className="text-sm text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
          >
            Cancel
          </Link>
        </div>

        {/* ── Crag section ─────────────────────────────────────── */}
        <section className="mb-6 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <h2 className="mb-3 text-sm font-medium text-zinc-900 dark:text-zinc-100">
            Crag
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {/* Crag name with autocomplete */}
            <div className="relative sm:col-span-2">
              <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
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
                className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
              />
              {showCragDropdown && filteredCrags.length > 0 && (
                <div
                  ref={dropdownRef}
                  className="absolute left-0 right-0 top-full z-10 mt-1 max-h-48 overflow-y-auto rounded-lg border border-zinc-200 bg-white shadow-lg dark:border-zinc-700 dark:bg-zinc-900"
                >
                  {filteredCrags.slice(0, 20).map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => selectCrag(c)}
                      className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    >
                      <span className="text-zinc-900 dark:text-zinc-100">
                        {c.name}
                      </span>
                      {c.country && (
                        <span className="text-xs text-zinc-400">
                          {c.country}
                        </span>
                      )}
                      <span className="ml-auto rounded-full bg-zinc-100 px-1.5 py-0.5 text-[10px] text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
                        {c.venue_type === "indoor_gym" ? "gym" : "outdoor"}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Venue type */}
            <div>
              <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
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
                className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
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
              <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
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
                className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
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
              <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
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
                className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
              />
            </div>

            {/* Region */}
            <div>
              <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
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
                className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
              />
            </div>
          </div>
        </section>

        {/* ── Date section ─────────────────────────────────────── */}
        <section className="mb-6 rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="flex items-center gap-4">
            <div>
              <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
                Date
              </label>
              <input
                type="date"
                value={form.date}
                max={new Date().toISOString().slice(0, 10)}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, date: e.target.value }))
                }
                className="rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
              />
            </div>
          </div>
        </section>

        {/* ── Ascents section ──────────────────────────────────── */}
        <section className="mb-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
              Ascents ({form.ascents.length})
            </h2>
            <button
              type="button"
              onClick={addAscent}
              className="rounded-lg border border-zinc-300 px-3 py-1 text-xs text-zinc-600 hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-400 dark:hover:bg-zinc-800"
            >
              + Add ascent
            </button>
          </div>

          <div className="space-y-3">
            {form.ascents.map((a, i) => (
              <div
                key={i}
                className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900"
              >
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-xs font-medium text-zinc-400">
                    #{i + 1}
                  </span>
                  {form.ascents.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeAscent(i)}
                      className="text-xs text-zinc-400 hover:text-red-500"
                    >
                      Remove
                    </button>
                  )}
                </div>

                {/* Row 1: Route + Grade */}
                <div className="mb-2 grid grid-cols-[1fr_100px] gap-2">
                  {!isGym ? (
                    <div>
                      <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
                        Route
                      </label>
                      <input
                        type="text"
                        value={a.route_name}
                        onChange={(e) =>
                          updateAscent(i, { route_name: e.target.value })
                        }
                        placeholder="Route name"
                        className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
                      />
                    </div>
                  ) : (
                    <div>
                      <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
                        Route (optional)
                      </label>
                      <input
                        type="text"
                        value={a.route_name}
                        onChange={(e) =>
                          updateAscent(i, { route_name: e.target.value })
                        }
                        placeholder="Optional"
                        className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
                      />
                    </div>
                  )}
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
                      Grade
                    </label>
                    <input
                      type="text"
                      value={a.grade}
                      onChange={(e) =>
                        updateAscent(i, { grade: e.target.value })
                      }
                      placeholder="e.g. 8a"
                      className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
                    />
                  </div>
                </div>

                {/* Row 2: Tick type + Style + Tries */}
                <div className="mb-2 grid grid-cols-3 gap-2">
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
                      Tick type
                    </label>
                    <select
                      value={a.tick_type}
                      onChange={(e) =>
                        updateAscent(i, { tick_type: e.target.value })
                      }
                      className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
                    >
                      {TICK_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t.charAt(0).toUpperCase() + t.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
                      Style
                    </label>
                    <select
                      value={a.style}
                      onChange={(e) =>
                        updateAscent(i, { style: e.target.value })
                      }
                      className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
                    >
                      {STYLES.map((s) => (
                        <option key={s} value={s}>
                          {s.replace("_", " ")}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
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
                      className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
                    />
                  </div>
                </div>

                {/* Row 3: Rating + Partner */}
                <div className="mb-2 grid grid-cols-2 gap-2">
                  <div>
                    <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
                      Rating
                    </label>
                    <select
                      value={a.rating}
                      onChange={(e) =>
                        updateAscent(i, { rating: e.target.value })
                      }
                      className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
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
                    <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
                      Partner
                    </label>
                    <input
                      type="text"
                      value={a.partner}
                      onChange={(e) =>
                        updateAscent(i, { partner: e.target.value })
                      }
                      placeholder="Optional"
                      className="w-full rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
                    />
                  </div>
                </div>

                {/* Row 4: Notes */}
                <div>
                  <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
                    Notes
                  </label>
                  <textarea
                    value={a.notes}
                    onChange={(e) =>
                      updateAscent(i, { notes: e.target.value })
                    }
                    placeholder="Optional notes"
                    rows={2}
                    className="w-full resize-none rounded-lg border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-sm text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100"
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Add ascent (bottom) */}
          <button
            type="button"
            onClick={addAscent}
            className="mt-3 w-full rounded-xl border border-dashed border-zinc-300 py-2.5 text-sm text-zinc-500 hover:border-zinc-400 hover:text-zinc-700 dark:border-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-600"
          >
            + Add another ascent
          </button>
        </section>

        {/* ── Error ────────────────────────────────────────────── */}
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}

        {/* ── Submit ───────────────────────────────────────────── */}
        <div className="flex justify-end gap-3 pb-8">
          <Link
            href="/log"
            className="rounded-lg px-4 py-2 text-sm text-zinc-500 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
          >
            Cancel
          </Link>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={saving}
            className="rounded-lg bg-zinc-900 px-5 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            {saving ? "Saving..." : "Save session"}
          </button>
        </div>
      </div>
    </div>
  );
}
