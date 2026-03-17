"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { listCrags, type CragWithStatsResponse } from "@/lib/api";

interface CragComboboxProps {
  value: number | null;
  onChange: (cragId: number, cragName: string) => void;
  excludeId?: number;
}

export default function CragCombobox({
  value,
  onChange,
  excludeId,
}: CragComboboxProps) {
  const [query, setQuery] = useState("");
  const [crags, setCrags] = useState<CragWithStatsResponse[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Load crags on mount and when query changes
  const loadCrags = useCallback(async (search: string) => {
    setLoading(true);
    try {
      const results = await listCrags({
        search: search || undefined,
        sort: "last_visited",
        limit: 50,
      });
      setCrags(results);
    } catch {
      // silently fail — keep existing list
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCrags(query);
  }, [query, loadCrags]);

  // Close on click outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const filtered = crags.filter((c) => excludeId == null || c.id !== excludeId);

  return (
    <div ref={wrapperRef} className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder="Search crags..."
        className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:ring-2 focus:ring-emerald-600 outline-none"
      />
      {open && (
        <div className="absolute z-50 mt-1 max-h-48 w-full overflow-y-auto rounded-lg border border-slate-700 bg-slate-800 shadow-lg">
          {loading && filtered.length === 0 && (
            <div className="px-3 py-2 text-xs text-slate-500">Loading...</div>
          )}
          {!loading && filtered.length === 0 && (
            <div className="px-3 py-2 text-xs text-slate-500">
              No crags found
            </div>
          )}
          {filtered.map((crag) => (
            <button
              key={crag.id}
              type="button"
              onClick={() => {
                onChange(crag.id, crag.name);
                setQuery(crag.name);
                setOpen(false);
              }}
              className={`w-full px-3 py-2 text-left text-sm hover:bg-slate-700 ${
                crag.id === value
                  ? "bg-slate-700 text-emerald-400"
                  : "text-slate-200"
              }`}
            >
              <span>{crag.name}</span>
              {crag.country && (
                <span className="ml-2 text-xs text-slate-500">
                  {crag.country}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
