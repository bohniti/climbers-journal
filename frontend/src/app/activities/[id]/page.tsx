"use client";

import { useEffect, useState } from "react";
import {
  api,
  Activity,
  ActivityPhoto,
  ActivityType,
  SessionRoute,
  SessionRouteCreate,
  GradeSystem,
  ClimbStyle,
  ACTIVITY_TYPE_LABELS,
  ACTIVITY_TYPE_COLORS,
  ACTIVITY_TYPE_TAGS,
} from "@/lib/api";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import PhotoGallery from "@/components/PhotoGallery";

const ACTIVITY_TYPES = Object.keys(ACTIVITY_TYPE_LABELS) as ActivityType[];
const GRADE_SYSTEMS: GradeSystem[] = ["yds", "french", "font", "uiaa", "ice_wis", "alpine", "vscale"];
const CLIMB_STYLES: ClimbStyle[] = ["onsight", "flash", "redpoint", "top_rope", "attempt", "aid", "solo"];

const IS_CLIMBING: ActivityType[] = ["bouldering", "sport_climb", "multi_pitch"];

// ─── Small helper components ──────────────────────────────────────────────────

function Field({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex gap-2 py-2.5 px-4 text-sm border-b border-slate-800 last:border-0">
      <span className="text-slate-500 w-40 shrink-0">{label}</span>
      <span className="text-slate-200">{String(value)}</span>
    </div>
  );
}

const inputCls =
  "w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-emerald-600";

// ─── Route row ─────────────────────────────────────────────────────────────────

function RouteRow({
  route,
  onUpdate,
  onDelete,
}: {
  route: SessionRoute;
  onUpdate: (updated: SessionRoute) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<SessionRouteCreate>({ ...route });
  const [saving, setSaving] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);

  const setF = (k: keyof SessionRouteCreate, v: string | number | null) =>
    setForm((f) => ({ ...f, [k]: v === "" ? null : v }));

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await api.routes.update(route.id, form);
      onUpdate(updated);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    await api.routes.delete(route.id);
    onDelete();
  };

  if (editing) {
    return (
      <div className="p-3 border border-slate-700 rounded-lg bg-slate-800/50 space-y-3">
        <div className="grid grid-cols-2 gap-2">
          <div className="col-span-2">
            <label className="block text-xs text-slate-500 mb-1">Route name</label>
            <input className={inputCls} value={form.route_name ?? ""} onChange={(e) => setF("route_name", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Grade</label>
            <input className={inputCls} value={form.grade ?? ""} onChange={(e) => setF("grade", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">System</label>
            <select className={inputCls} value={form.grade_system ?? ""} onChange={(e) => setF("grade_system", e.target.value)}>
              <option value="">—</option>
              {GRADE_SYSTEMS.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Style</label>
            <select className={inputCls} value={form.style ?? ""} onChange={(e) => setF("style", e.target.value)}>
              <option value="">—</option>
              {CLIMB_STYLES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Pitches</label>
            <input
              type="number" min={1} className={inputCls}
              value={form.pitches ?? ""}
              onChange={(e) => setF("pitches", e.target.value ? Number(e.target.value) : null)}
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Height (m)</label>
            <input
              type="number" className={inputCls}
              value={form.height_m ?? ""}
              onChange={(e) => setF("height_m", e.target.value ? Number(e.target.value) : null)}
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Sector</label>
            <input className={inputCls} value={form.sector ?? ""} onChange={(e) => setF("sector", e.target.value)} />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Tries</label>
            <input
              type="number" min={1} className={inputCls}
              value={form.tries ?? ""}
              onChange={(e) => setF("tries", e.target.value ? Number(e.target.value) : null)}
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Stars (0–3)</label>
            <input
              type="number" min={0} max={3} className={inputCls}
              value={form.stars ?? ""}
              onChange={(e) => setF("stars", e.target.value ? Number(e.target.value) : null)}
            />
          </div>
          <div className="col-span-2">
            <label className="block text-xs text-slate-500 mb-1">URL (thecrag / bergsteigen)</label>
            <input className={inputCls} value={form.url ?? ""} onChange={(e) => setF("url", e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="block text-xs text-slate-500 mb-1">Notes</label>
            <input className={inputCls} value={form.notes ?? ""} onChange={(e) => setF("notes", e.target.value)} />
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-xs text-white rounded-lg transition-colors"
          >
            {saving ? "…" : "Save"}
          </button>
          <button
            onClick={() => setEditing(false)}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-xs text-slate-200 rounded-lg transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 p-3 border border-slate-800 rounded-lg text-sm">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          {route.url ? (
            <a
              href={route.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-200 font-medium hover:text-emerald-400 transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              {route.route_name || "Unnamed"} ↗
            </a>
          ) : (
            <span className="text-slate-200 font-medium">{route.route_name || "Unnamed"}</span>
          )}
          {route.stars != null && route.stars > 0 && (
            <span className="text-yellow-400 text-xs">{"★".repeat(route.stars)}</span>
          )}
        </div>
        <div className="flex gap-2 mt-0.5 text-xs text-slate-500">
          {route.grade && (
            <span className="font-mono bg-slate-800 px-1.5 py-0.5 rounded">
              {route.grade}{route.grade_system ? ` (${route.grade_system})` : ""}
            </span>
          )}
          {route.style && <span className="capitalize">{route.style.replace(/_/g, " ")}</span>}
          {route.tries != null && <span>{route.tries} {route.tries === 1 ? "try" : "tries"}</span>}
          {route.pitches && <span>{route.pitches}p</span>}
          {route.height_m && <span>{route.height_m} m</span>}
          {route.sector && <span>{route.sector}</span>}
        </div>
      </div>
      <div className="flex gap-1 shrink-0">
        <button
          onClick={() => setEditing(true)}
          className="px-2 py-1 text-xs border border-slate-700 hover:border-slate-500 text-slate-400 hover:text-slate-200 rounded transition-colors"
        >
          Edit
        </button>
        {!confirmDel ? (
          <button
            onClick={() => setConfirmDel(true)}
            className="px-2 py-1 text-xs border border-slate-800 hover:border-red-800 text-slate-500 hover:text-red-400 rounded transition-colors"
          >
            ✕
          </button>
        ) : (
          <>
            <button
              onClick={handleDelete}
              className="px-2 py-1 text-xs bg-red-800 hover:bg-red-700 text-white rounded transition-colors"
            >
              Delete
            </button>
            <button
              onClick={() => setConfirmDel(false)}
              className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 rounded transition-colors"
            >
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ─── Add route form ───────────────────────────────────────────────────────────

function AddRouteForm({
  activityId,
  onAdded,
  onCancel,
}: {
  activityId: number;
  onAdded: (r: SessionRoute) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<SessionRouteCreate>({});
  const [saving, setSaving] = useState(false);

  const setF = (k: keyof SessionRouteCreate, v: string | number | null) =>
    setForm((f) => ({ ...f, [k]: v === "" ? null : v }));

  const handleAdd = async () => {
    setSaving(true);
    try {
      const r = await api.routes.create(activityId, form);
      onAdded(r);
      setForm({});
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-3 border border-emerald-900 rounded-lg bg-slate-800/50 space-y-3">
      <p className="text-xs text-emerald-400 font-medium">Add Route</p>
      <div className="grid grid-cols-2 gap-2">
        <div className="col-span-2">
          <label className="block text-xs text-slate-500 mb-1">Route name</label>
          <input className={inputCls} value={form.route_name ?? ""} onChange={(e) => setF("route_name", e.target.value)} placeholder="e.g. Traumtänzer" />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Grade</label>
          <input className={inputCls} value={form.grade ?? ""} onChange={(e) => setF("grade", e.target.value)} placeholder="e.g. 7a" />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">System</label>
          <select className={inputCls} value={form.grade_system ?? ""} onChange={(e) => setF("grade_system", e.target.value)}>
            <option value="">—</option>
            {GRADE_SYSTEMS.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Style</label>
          <select className={inputCls} value={form.style ?? ""} onChange={(e) => setF("style", e.target.value)}>
            <option value="">—</option>
            {CLIMB_STYLES.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Pitches</label>
          <input
            type="number" min={1} className={inputCls}
            value={form.pitches ?? ""}
            onChange={(e) => setF("pitches", e.target.value ? Number(e.target.value) : null)}
          />
        </div>
      </div>
      <div className="flex gap-2">
        <button
          onClick={handleAdd}
          disabled={saving}
          className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-xs text-white rounded-lg transition-colors"
        >
          {saving ? "Adding…" : "Add Route"}
        </button>
        <button
          onClick={onCancel}
          className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-xs text-slate-200 rounded-lg transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ─── Edit form ────────────────────────────────────────────────────────────────

function EditForm({
  activity,
  onSave,
  onCancel,
}: {
  activity: Activity;
  onSave: (updated: Activity) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<Partial<Activity>>({ ...activity });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (key: keyof Activity, value: string | number | null | string[]) =>
    setForm((f) => ({ ...f, [key]: value === "" ? null : value }));

  const toggleTag = (tag: string) => {
    const current = form.tags || [];
    const next = current.includes(tag) ? current.filter((t) => t !== tag) : [...current, tag];
    setForm((f) => ({ ...f, tags: next }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.activities.update(activity.id, form);
      onSave(updated);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const selectedType = (form.activity_type as ActivityType) || "other";
  const suggestedTags = ACTIVITY_TYPE_TAGS[selectedType] || [];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        {/* Title */}
        <div className="col-span-2">
          <label className="block text-xs text-slate-500 mb-1">Title</label>
          <input className={inputCls} value={form.title ?? ""} onChange={(e) => set("title", e.target.value)} />
        </div>

        {/* Type */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Type</label>
          <select className={inputCls} value={form.activity_type ?? ""} onChange={(e) => set("activity_type", e.target.value)}>
            {ACTIVITY_TYPES.map((t) => (
              <option key={t} value={t}>{ACTIVITY_TYPE_LABELS[t]}</option>
            ))}
          </select>
        </div>

        {/* Date */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Date</label>
          <input
            type="date"
            className={inputCls}
            value={form.date ? form.date.slice(0, 10) : ""}
            onChange={(e) => set("date", e.target.value + "T00:00:00")}
          />
        </div>

        {/* Tags */}
        <div className="col-span-2">
          <label className="block text-xs text-slate-500 mb-2">Tags</label>
          <div className="flex flex-wrap gap-2">
            {suggestedTags.map((tag) => {
              const active = (form.tags || []).includes(tag);
              return (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleTag(tag)}
                  className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                    active
                      ? "bg-emerald-800 border-emerald-600 text-emerald-200"
                      : "border-slate-700 text-slate-400 hover:border-slate-500"
                  }`}
                >
                  {tag.replace(/_/g, " ")}
                </button>
              );
            })}
          </div>
        </div>

        {/* Region */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Region</label>
          <input className={inputCls} placeholder="e.g. Fränkische Schweiz, Hohe Wand, Kletterhalle Wien" value={form.region ?? ""} onChange={(e) => set("region", e.target.value)} />
        </div>

        {/* Area */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Area / Crag</label>
          <input className={inputCls} value={form.area ?? ""} onChange={(e) => set("area", e.target.value)} />
        </div>

        {/* Partner */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Partner</label>
          <input className={inputCls} value={form.partner ?? ""} onChange={(e) => set("partner", e.target.value)} />
        </div>

        {/* Duration */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Duration (minutes)</label>
          <input
            type="number" className={inputCls}
            value={form.duration_minutes ?? ""}
            onChange={(e) => set("duration_minutes", e.target.value ? Number(e.target.value) : null)}
          />
        </div>

        {/* Elevation gain */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Elevation gain (m)</label>
          <input
            type="number" className={inputCls}
            value={form.elevation_gain_m ?? ""}
            onChange={(e) => set("elevation_gain_m", e.target.value ? Number(e.target.value) : null)}
          />
        </div>

        {/* Distance */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Distance (km)</label>
          <input
            type="number" step="0.01" className={inputCls}
            value={form.distance_km ?? ""}
            onChange={(e) => set("distance_km", e.target.value ? Number(e.target.value) : null)}
          />
        </div>

        {/* Avg heart rate */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Avg heart rate (bpm)</label>
          <input
            type="number" className={inputCls}
            value={form.avg_heart_rate ?? ""}
            onChange={(e) => set("avg_heart_rate", e.target.value ? Number(e.target.value) : null)}
          />
        </div>

        {/* Calories */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Calories (kcal)</label>
          <input
            type="number" className={inputCls}
            value={form.calories ?? ""}
            onChange={(e) => set("calories", e.target.value ? Number(e.target.value) : null)}
          />
        </div>

        {/* Location name */}
        <div>
          <label className="block text-xs text-slate-500 mb-1">Location name</label>
          <input className={inputCls} value={form.location_name ?? ""} onChange={(e) => set("location_name", e.target.value)} />
        </div>

        {/* Notes */}
        <div className="col-span-2">
          <label className="block text-xs text-slate-500 mb-1">Notes</label>
          <textarea
            rows={3} className={inputCls + " resize-none"}
            value={form.notes ?? ""}
            onChange={(e) => set("notes", e.target.value)}
          />
        </div>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="flex gap-2 pt-1">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-sm font-medium transition-colors"
        >
          {saving ? "Saving…" : "Save changes"}
        </button>
        <button
          onClick={onCancel}
          disabled={saving}
          className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function ActivityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [activity, setActivity] = useState<Activity | null>(null);
  const [routes, setRoutes] = useState<SessionRoute[]>([]);
  const [photos, setPhotos] = useState<ActivityPhoto[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [addingRoute, setAddingRoute] = useState(false);


  useEffect(() => {
    const numId = Number(id);
    Promise.all([
      api.activities.get(numId),
      api.routes.list(numId).catch(() => [] as SessionRoute[]),
      api.photos.list(numId).catch(() => [] as ActivityPhoto[]),
    ])
      .then(([act, rts, pht]) => {
        setActivity(act);
        setRoutes(rts);
        setPhotos(pht);
      })
      .catch(() => router.push("/activities"))
      .finally(() => setLoading(false));
  }, [id, router]);

  const handleDelete = async () => {
    setDeleting(true);
    await api.activities.delete(Number(id));
    router.push("/activities");
  };

  if (loading) return <div className="text-slate-400 p-4">Loading…</div>;
  if (!activity) return null;

  const isClimbing = IS_CLIMBING.includes(activity.activity_type as ActivityType);

  const fields: [string, string | number][] = (
    [
      ["Date", new Date(activity.date).toLocaleDateString()],
      ["Region", activity.region],
      ["Area", activity.area],
      ["Location", activity.location_name],
      ["Partner", activity.partner],
      ["Duration", activity.duration_minutes ? `${Math.floor(activity.duration_minutes / 60)}h ${activity.duration_minutes % 60}m` : undefined],
      ["Distance", activity.distance_km ? `${activity.distance_km} km` : undefined],
      ["Elevation gain", activity.elevation_gain_m ? `${activity.elevation_gain_m.toLocaleString()} m` : undefined],
      ["Avg heart rate", activity.avg_heart_rate ? `${activity.avg_heart_rate} bpm` : undefined],
      ["Calories", activity.calories ? `${activity.calories} kcal` : undefined],
      ["Source", activity.source],
      ["Garmin ID", activity.intervals_activity_id],
    ] as [string, string | number | undefined | null][]
  ).filter(([, v]) => v != null && v !== "") as [string, string | number][];

  return (
    <div className="max-w-2xl">
      {/* Breadcrumb */}
      <div className="mb-4">
        <Link href="/activities" className="text-sm text-slate-500 hover:text-slate-300">
          ← Activities
        </Link>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 mb-2">{activity.title}</h1>
          {/* Type badge + tags */}
          <div className="flex flex-wrap gap-1.5">
            <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${ACTIVITY_TYPE_COLORS[activity.activity_type as ActivityType] ?? "bg-slate-800 text-slate-400"}`}>
              {ACTIVITY_TYPE_LABELS[activity.activity_type as ActivityType] ?? activity.activity_type}
            </span>
            {(activity.tags || []).map((tag) => (
              <span key={tag} className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-400">
                {tag.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </div>

        {!editing && (
          <div className="flex gap-2 shrink-0">
            <Link
              href={`/coach?activity=${id}`}
              className="px-3 py-1.5 rounded-lg border border-purple-800 hover:border-purple-600 text-sm text-purple-400 hover:text-purple-300 transition-colors"
            >
              Ask Coach
            </Link>
            <button
              onClick={() => setEditing(true)}
              className="px-3 py-1.5 rounded-lg border border-slate-700 hover:border-slate-500 text-sm text-slate-300 hover:text-slate-100 transition-colors"
            >
              Edit
            </button>
            {!confirmDelete ? (
              <button
                onClick={() => setConfirmDelete(true)}
                className="px-3 py-1.5 rounded-lg border border-red-900 hover:border-red-700 text-sm text-red-400 hover:text-red-300 transition-colors"
              >
                Delete
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-sm text-red-400">Delete?</span>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="px-3 py-1.5 rounded-lg bg-red-800 hover:bg-red-700 disabled:opacity-50 text-sm text-white transition-colors"
                >
                  {deleting ? "…" : "Yes"}
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm transition-colors"
                >
                  No
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* View or Edit */}
      {editing ? (
        <div className="space-y-6">
          <EditForm
            activity={activity}
            onSave={(updated) => { setActivity(updated); setEditing(false); }}
            onCancel={() => setEditing(false)}
          />
          <PhotoGallery
            activityId={activity.id}
            photos={photos}
            onPhotosChange={setPhotos}
            editable={true}
          />
        </div>
      ) : (
        <>
          <div className="rounded-xl border border-slate-800 overflow-hidden mb-4">
            {fields.map(([label, value]) => (
              <Field key={label} label={label} value={value} />
            ))}
          </div>

          {activity.notes && (
            <div className="mb-4 p-4 rounded-xl border border-slate-800 bg-slate-900/30">
              <h3 className="text-sm font-medium text-slate-400 mb-2">Notes</h3>
              <p className="text-slate-200 text-sm whitespace-pre-wrap">{activity.notes}</p>
            </div>
          )}

          {/* Photos */}
          <div className="mb-4">
            <PhotoGallery
              activityId={activity.id}
              photos={photos}
              onPhotosChange={setPhotos}
              editable={false}
            />
          </div>

          {/* Routes section — only for climbing activities */}
          {isClimbing && (
            <div className="mt-2">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-slate-300">
                  Routes
                  {routes.length > 0 && (
                    <span className="ml-2 text-xs text-slate-500">({routes.length})</span>
                  )}
                </h3>
                {!addingRoute && (
                  <button
                    onClick={() => setAddingRoute(true)}
                    className="text-xs px-3 py-1.5 border border-emerald-800 hover:border-emerald-600 text-emerald-400 hover:text-emerald-300 rounded-lg transition-colors"
                  >
                    + Add Route
                  </button>
                )}
              </div>

              <div className="space-y-2">
                {routes.map((r) => (
                  <RouteRow
                    key={r.id}
                    route={r}
                    onUpdate={(updated) =>
                      setRoutes((rs) => rs.map((x) => (x.id === updated.id ? updated : x)))
                    }
                    onDelete={() => setRoutes((rs) => rs.filter((x) => x.id !== r.id))}
                  />
                ))}

                {addingRoute && (
                  <AddRouteForm
                    activityId={activity.id}
                    onAdded={(r) => {
                      setRoutes((rs) => [...rs, r]);
                      setAddingRoute(false);
                    }}
                    onCancel={() => setAddingRoute(false)}
                  />
                )}

                {routes.length === 0 && !addingRoute && (
                  <p className="text-xs text-slate-600 py-2">No routes logged yet.</p>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
