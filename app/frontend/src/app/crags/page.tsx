"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { listCrags, type CragWithStatsResponse } from "@/lib/api";
import { VenueIcon } from "@/components/ActivityIcon";

type SortOption = "last_visited" | "name" | "session_count";

const PAGE_SIZE = 50;

export default function CragsPage() {
  const [crags, setCrags] = useState<CragWithStatsResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortOption>("last_visited");
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  // Debounced search
  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const fetchCrags = useCallback(
    async (currentOffset: number, append: boolean) => {
      setLoading(true);
      setError(null);
      try {
        const data = await listCrags({
          search: debouncedSearch || undefined,
          sort,
          offset: currentOffset,
          limit: PAGE_SIZE,
        });
        setHasMore(data.length === PAGE_SIZE);
        setOffset(currentOffset + data.length);
        if (append) {
          setCrags((prev) => [...prev, ...data]);
        } else {
          setCrags(data);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load crags");
      } finally {
        setLoading(false);
      }
    },
    [debouncedSearch, sort]
  );

  useEffect(() => {
    setOffset(0);
    fetchCrags(0, false);
  }, [fetchCrags]);

  const loadMore = () => fetchCrags(offset, true);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="shrink-0 border-b border-slate-700 bg-slate-900 px-4 py-3">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-3">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search crags..."
            className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500"
          />
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortOption)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
          >
            <option value="last_visited">Last visited</option>
            <option value="name">Name</option>
            <option value="session_count">Most sessions</option>
          </select>
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-4">
          {error && (
            <div className="mb-4 rounded-lg border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          {!loading && crags.length === 0 && (
            <div className="pt-24 text-center text-slate-500">
              <p className="text-lg">No crags found</p>
              <p className="mt-1 text-sm">
                Log a climbing session to add your first crag
              </p>
            </div>
          )}

          <div className="space-y-2">
            {crags.map((crag) => (
              <CragRow key={crag.id} crag={crag} />
            ))}
          </div>

          {loading && (
            <div className="py-8 text-center text-sm text-slate-400">
              Loading...
            </div>
          )}
          {!loading && hasMore && crags.length > 0 && (
            <div className="py-6 text-center">
              <button
                onClick={loadMore}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-800"
              >
                Load more
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CragRow({ crag }: { crag: CragWithStatsResponse }) {
  const venueLabel = crag.venue_type === "indoor_gym" ? "Gym" : "Outdoor";

  const relativeDate = crag.last_visited
    ? formatRelative(crag.last_visited)
    : null;

  return (
    <Link
      href={`/crags/${crag.id}`}
      className="block rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 transition-colors hover:border-slate-600"
    >
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-800">
          <VenueIcon venueType={crag.venue_type} size="md" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium text-slate-100">
              {crag.name}
            </span>
            <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-medium text-slate-400">
              {venueLabel}
            </span>
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-400">
            {crag.country && <span>{crag.country}</span>}
            {crag.country && crag.region && <span>&middot;</span>}
            {crag.region && <span>{crag.region}</span>}
            {(crag.country || crag.region) && <span>&middot;</span>}
            <span>
              {crag.session_count} session{crag.session_count !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
        {relativeDate && (
          <span className="shrink-0 text-xs text-slate-500">
            {relativeDate}
          </span>
        )}
      </div>
    </Link>
  );
}

function formatRelative(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  const now = new Date();
  const diff = Math.floor(
    (now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24)
  );
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  if (diff < 7) return `${diff} days ago`;
  if (diff < 30) {
    const weeks = Math.floor(diff / 7);
    return `${weeks} week${weeks !== 1 ? "s" : ""} ago`;
  }
  if (diff < 365) {
    const months = Math.floor(diff / 30);
    return `${months} month${months !== 1 ? "s" : ""} ago`;
  }
  const years = Math.floor(diff / 365);
  return `${years} year${years !== 1 ? "s" : ""} ago`;
}
