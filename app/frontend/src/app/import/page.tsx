"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchConfigStatus,
  importClimbingCsv,
  syncIntervals,
  type ConfigStatus,
  type ImportResponse,
  type SyncResponse,
} from "@/lib/api";

const inputClass =
  "w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-600";

export default function ImportPage() {
  const [config, setConfig] = useState<ConfigStatus | null>(null);

  // Climbing CSV state
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvLoading, setCsvLoading] = useState(false);
  const [csvResult, setCsvResult] = useState<ImportResponse | null>(null);
  const [csvError, setCsvError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync state
  const [oldest, setOldest] = useState("");
  const [newest, setNewest] = useState("");
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResponse | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  useEffect(() => {
    fetchConfigStatus()
      .then(setConfig)
      .catch(() => setConfig({ intervals_configured: false, llm_configured: false }));
  }, []);

  // Default date range: last 6 months to today
  useEffect(() => {
    const today = new Date();
    const sixMonthsAgo = new Date(today);
    sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
    setNewest(today.toISOString().slice(0, 10));
    setOldest(sixMonthsAgo.toISOString().slice(0, 10));
  }, []);

  const handleCsvUpload = useCallback(async () => {
    if (!csvFile) return;
    setCsvLoading(true);
    setCsvError(null);
    setCsvResult(null);
    try {
      const result = await importClimbingCsv(csvFile);
      setCsvResult(result);
    } catch (e) {
      setCsvError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setCsvLoading(false);
    }
  }, [csvFile]);

  const handleSync = useCallback(async () => {
    if (!oldest || !newest) return;
    setSyncLoading(true);
    setSyncError(null);
    setSyncResult(null);
    try {
      const result = await syncIntervals(oldest, newest);
      setSyncResult(result);
    } catch (e) {
      setSyncError(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncLoading(false);
    }
  }, [oldest, newest]);

  const intervalsDisabled = config !== null && !config.intervals_configured;

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Import Data</h1>
        <p className="mt-1 text-sm text-slate-400">
          Bring in your climbing history and endurance activities.
        </p>
      </div>

      {/* ── Climbing CSV Card ───────────────────────────────── */}
      <div className="rounded-xl border border-slate-700 bg-slate-900 p-5 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Climbing History</h2>
          <p className="mt-1 text-sm text-slate-400">
            Upload a CSV file with your climbing ascents.
          </p>
        </div>

        <div className="space-y-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            onChange={(e) => {
              setCsvFile(e.target.files?.[0] ?? null);
              setCsvResult(null);
              setCsvError(null);
            }}
            className={inputClass}
          />

          {csvFile && (
            <p className="text-xs text-slate-400">
              Selected: {csvFile.name} ({(csvFile.size / 1024).toFixed(1)} KB)
            </p>
          )}

          <button
            onClick={handleCsvUpload}
            disabled={!csvFile || csvLoading}
            className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {csvLoading && <Spinner />}
            {csvLoading ? "Uploading..." : "Upload CSV"}
          </button>
        </div>

        {csvResult && (
          <div className="rounded-lg border border-emerald-700 bg-emerald-950/40 p-3 text-sm space-y-1">
            <p className="font-medium text-emerald-300">Import complete</p>
            <p className="text-slate-300">
              {csvResult.created} created, {csvResult.skipped} skipped, {csvResult.rows_imported} rows processed
            </p>
            {csvResult.errors.length > 0 && (
              <div className="mt-2 space-y-1">
                <p className="text-yellow-400 font-medium">
                  {csvResult.errors.length} error{csvResult.errors.length !== 1 && "s"}:
                </p>
                <ul className="list-disc list-inside text-yellow-400/80 text-xs">
                  {csvResult.errors.slice(0, 10).map((err) => (
                    <li key={err.row}>
                      Row {err.row}: {err.reason}
                    </li>
                  ))}
                  {csvResult.errors.length > 10 && (
                    <li>...and {csvResult.errors.length - 10} more</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        )}

        {csvError && (
          <div className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-400">
            {csvError}
          </div>
        )}
      </div>

      {/* ── Endurance Sync Card ─────────────────────────────── */}
      <div
        className={`rounded-xl border bg-slate-900 p-5 space-y-4 ${
          intervalsDisabled ? "border-slate-800 opacity-60" : "border-slate-700"
        }`}
      >
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Endurance Activities</h2>
          <p className="mt-1 text-sm text-slate-400">
            Sync activities from intervals.icu for a date range.
          </p>
        </div>

        {intervalsDisabled && (
          <div className="rounded-lg border border-yellow-700 bg-yellow-950/30 p-3 text-sm text-yellow-400">
            intervals.icu is not configured. Set <code className="font-mono">INTERVALS_API_KEY</code> and{" "}
            <code className="font-mono">INTERVALS_ATHLETE_ID</code> in your <code className="font-mono">.env</code> file.
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">From</label>
            <input
              type="date"
              value={oldest}
              onChange={(e) => setOldest(e.target.value)}
              disabled={intervalsDisabled}
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">To</label>
            <input
              type="date"
              value={newest}
              onChange={(e) => setNewest(e.target.value)}
              disabled={intervalsDisabled}
              className={inputClass}
            />
          </div>
        </div>

        <button
          onClick={handleSync}
          disabled={intervalsDisabled || syncLoading || !oldest || !newest}
          className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {syncLoading && <Spinner />}
          {syncLoading ? "Syncing..." : "Sync from intervals.icu"}
        </button>

        {syncResult && (
          <div className="rounded-lg border border-emerald-700 bg-emerald-950/40 p-3 text-sm space-y-1">
            <p className="font-medium text-emerald-300">Sync complete</p>
            <p className="text-slate-300">
              {syncResult.total_created} created, {syncResult.total_updated} updated across{" "}
              {syncResult.synced.length} month{syncResult.synced.length !== 1 && "s"}
            </p>
            {syncResult.failed.length > 0 && (
              <div className="mt-2 space-y-1">
                <p className="text-yellow-400 font-medium">
                  {syncResult.failed.length} month{syncResult.failed.length !== 1 && "s"} failed:
                </p>
                <ul className="list-disc list-inside text-yellow-400/80 text-xs">
                  {syncResult.failed.map((f) => (
                    <li key={f.month}>
                      {f.month}: {f.error}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {syncError && (
          <div className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-400">
            {syncError}
          </div>
        )}
      </div>
    </div>
  );
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
