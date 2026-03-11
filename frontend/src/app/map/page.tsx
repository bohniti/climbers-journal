"use client";

import { useEffect, useRef, useState } from "react";
import { api, Activity, ActivityType, ACTIVITY_TYPE_LABELS, ACTIVITY_TYPE_HEX } from "@/lib/api";

// ─── Marker colours per activity type ────────────────────────────────────────
const TYPE_COLOR: Record<string, string> = {
  ...ACTIVITY_TYPE_HEX,
};

// ─── Types ────────────────────────────────────────────────────────────────────
type FilterType = ActivityType | "";

export default function MapPage() {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMap = useRef<import("leaflet").Map | null>(null);
  const markersRef = useRef<import("leaflet").CircleMarker[]>([]);

  const [activities, setActivities] = useState<Activity[]>([]);
  const [filterType, setFilterType] = useState<FilterType>("");
  const [mapReady, setMapReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(0);

  // ── 1. Load ALL activities (paginate in batches of 1000) ─────────────────
  useEffect(() => {
    (async () => {
      try {
        const all: Activity[] = [];
        let offset = 0;
        const BATCH = 1000;
        while (true) {
          const batch = await api.activities.list({ limit: BATCH, offset });
          all.push(...batch);
          if (batch.length < BATCH) break;
          offset += BATCH;
        }
        setActivities(all);
      } catch (e) {
        setLoadError((e as Error).message);
      }
    })();
  }, []);

  // ── 2. Init map (once, client-side only) ─────────────────────────────────
  useEffect(() => {
    if (!mapRef.current || leafletMap.current) return;

    let cancelled = false;

    (async () => {
      // Fetch runtime API key
      let apiKey: string;
      try {
        const res = await fetch("/config");
        const data = await res.json();
        if (!data.apiKey) throw new Error(data.error ?? "missing key");
        apiKey = data.apiKey;
      } catch (e) {
        if (!cancelled) setLoadError("Could not load map config: " + e);
        return;
      }

      // Dynamically import Leaflet (needs window)
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");

      if (cancelled || !mapRef.current) return;

      // Center on Austria/Alps by default
      const map = L.map(mapRef.current, { zoomControl: true }).setView([47.5, 13.5], 6);

      // Mapy.com outdoor tiles — great for climbing (terrain, trails, crags)
      L.tileLayer(
        `https://api.mapy.com/v1/maptiles/outdoor/256/{z}/{x}/{y}?apikey=${apiKey}&lang=en`,
        {
          maxZoom: 19,
          attribution:
            '&copy; <a href="https://mapy.com" target="_blank">Mapy.com</a> &copy; <a href="https://openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>',
        }
      ).addTo(map);

      leafletMap.current = map;
      setMapReady(true);
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // ── 3. Render / update markers whenever activities or filter changes ──────
  useEffect(() => {
    if (!mapReady || !leafletMap.current) return;

    (async () => {
      const L = (await import("leaflet")).default;
      const map = leafletMap.current!;

      // Remove old markers
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];

      const filtered = activities.filter(
        (a) => a.lat && a.lon && (filterType === "" || a.activity_type === filterType)
      );
      setVisibleCount(filtered.length);

      filtered.forEach((a) => {
        const color = TYPE_COLOR[a.activity_type] ?? "#94a3b8";
        const dateStr = new Date(a.date).toLocaleDateString("en-US", {
          day: "numeric",
          month: "short",
          year: "numeric",
        });

        const marker = L.circleMarker([a.lat!, a.lon!], {
          radius: 7,
          color: color,
          fillColor: color,
          fillOpacity: 0.85,
          weight: 1.5,
        });

        marker.bindPopup(
          `<div style="min-width:180px;font-family:sans-serif;font-size:13px">
            <div style="font-weight:600;margin-bottom:4px">${a.title}</div>
            ${a.region ? `<div style="color:#64748b;font-size:11px">${a.region}${a.area && a.area !== a.region ? ` › ${a.area}` : ""}</div>` : a.area ? `<div style="color:#64748b;font-size:11px">${a.area}</div>` : ""}
            <div style="color:#94a3b8;font-size:11px;margin-top:2px">${dateStr}</div>
            <a href="/activities/${a.id}" style="display:inline-block;margin-top:8px;font-size:11px;color:#10b981;text-decoration:none">View activity →</a>
          </div>`,
          { maxWidth: 260 }
        );

        marker.addTo(map);
        markersRef.current.push(marker);
      });

      // Auto-fit to visible markers if any
      if (filtered.length > 0 && markersRef.current.length > 0) {
        const group = L.featureGroup(markersRef.current);
        map.fitBounds(group.getBounds().pad(0.15), { maxZoom: 12 });
      }
    })();
  }, [mapReady, activities, filterType]);

  const withCoords = activities.filter((a) => a.lat && a.lon);

  return (
    <div style={{ position: "fixed", top: 57, left: 0, right: 0, bottom: 0, zIndex: 5 }}>
      {/* Filter bar */}
      <div className="absolute z-10 top-3 left-4 right-4 flex flex-wrap items-center gap-2 pointer-events-none">
        <div className="flex flex-wrap gap-2 pointer-events-auto bg-slate-900/90 backdrop-blur px-3 py-2 rounded-xl border border-slate-800 shadow-lg">
          <button
            onClick={() => setFilterType("")}
            className={`text-xs px-3 py-1 rounded-full border transition-colors ${
              filterType === ""
                ? "bg-slate-600 border-slate-500 text-white"
                : "border-slate-700 text-slate-400 hover:text-slate-200"
            }`}
          >
            All
          </button>
          {(Object.keys(ACTIVITY_TYPE_LABELS) as ActivityType[]).map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                filterType === t
                  ? "bg-slate-600 border-slate-500 text-white"
                  : "border-slate-700 text-slate-400 hover:text-slate-200"
              }`}
            >
              <span
                className="inline-block w-2 h-2 rounded-full mr-1.5"
                style={{ backgroundColor: TYPE_COLOR[t] }}
              />
              {ACTIVITY_TYPE_LABELS[t]}
            </button>
          ))}

          {/* Count */}
          <span className="text-xs text-slate-500 self-center pl-1">
            {visibleCount} / {withCoords.length} with GPS
          </span>
        </div>
      </div>

      {/* Error state */}
      {loadError && (
        <div className="absolute z-20 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-slate-900 border border-red-800 rounded-xl p-6 text-red-400 text-sm">
          {loadError}
        </div>
      )}

      {/* Map container — full height minus nav */}
      <div ref={mapRef} className="w-full h-full" />
    </div>
  );
}
