"use client";

import { Suspense, useState, useRef, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import {
  api,
  ChatMessage,
  Activity,
  SessionRouteCreate,
  CoachImageData,
  PendingUpdate,
  ACTIVITY_TYPE_LABELS,
} from "@/lib/api";
import Link from "next/link";

// ─── Activity proposal component ─────────────────────────────────────────────

function ActivityProposal({
  data,
  onSave,
  onReject,
  saving,
}: {
  data: Partial<Activity> & { routes?: SessionRouteCreate[] };
  onSave: () => void;
  onReject: () => void;
  saving: boolean;
}) {
  const rows: [string, string | number][] = (
    [
      ["Type", data.activity_type ? ACTIVITY_TYPE_LABELS[data.activity_type] : undefined],
      ["Tags", data.tags && data.tags.length > 0 ? data.tags.join(", ") : undefined],
      ["Date", data.date ? new Date(data.date).toLocaleDateString() : undefined],
      ["Area", data.area],
      ["Region", data.region],
      ["Location", data.location_name],
      ["Partner", data.partner],
      [
        "Duration",
        data.duration_minutes
          ? `${Math.floor(data.duration_minutes / 60)}h ${data.duration_minutes % 60}m`
          : undefined,
      ],
      ["Distance", data.distance_km ? `${data.distance_km} km` : undefined],
      ["Elevation gain", data.elevation_gain_m ? `${data.elevation_gain_m} m` : undefined],
      ["Notes", data.notes],
    ] as [string, string | number | undefined | null][]
  ).filter(([, v]) => v != null && v !== "") as [string, string | number][];

  const routes = (data as { routes?: SessionRouteCreate[] }).routes || [];

  return (
    <div className="rounded-xl border border-emerald-800 bg-emerald-950/20 p-4">
      <p className="text-xs font-semibold text-emerald-400 uppercase tracking-wide mb-3">
        New activity — please review
      </p>
      <div className="space-y-1.5 mb-3">
        {rows.map(([label, value]) => (
          <div key={label} className="flex gap-2 text-sm">
            <span className="text-slate-500 w-32 shrink-0">{label}</span>
            <span className="text-slate-200">{String(value)}</span>
          </div>
        ))}
      </div>
      {routes.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-slate-500 mb-1">Routes:</p>
          <div className="space-y-0.5">
            {routes.map((r, i) => (
              <div key={i} className="text-sm text-slate-300">
                {i + 1}. {r.route_name || `Route ${i + 1}`}
                {r.grade ? ` — ${r.grade}${r.grade_system ? ` (${r.grade_system})` : ""}` : ""}
                {r.style ? `, ${r.style}` : ""}
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="flex gap-2">
        <button
          onClick={onSave}
          disabled={saving}
          className="px-4 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-sm font-medium transition-colors"
        >
          {saving ? "Saving…" : "✓ Save activity"}
        </button>
        <button
          onClick={onReject}
          disabled={saving}
          className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-sm transition-colors"
        >
          ✗ Something&apos;s wrong
        </button>
      </div>
    </div>
  );
}

// ─── Update proposal component ────────────────────────────────────────────────

function UpdateProposal({
  update,
  onSave,
  onReject,
  saving,
}: {
  update: PendingUpdate;
  onSave: () => void;
  onReject: () => void;
  saving: boolean;
}) {
  const fields = Object.keys(update.changes);

  return (
    <div className="rounded-xl border border-blue-800 bg-blue-950/20 p-4">
      <p className="text-xs font-semibold text-blue-400 uppercase tracking-wide mb-3">
        Proposed changes — please review
      </p>
      <div className="space-y-2 mb-4">
        {fields.map((f) => (
          <div key={f} className="text-sm">
            <span className="text-xs font-medium text-slate-500 uppercase block">{f.replace(/_/g, " ")}</span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-red-400/70 line-through">
                {update.current_values[f] != null ? String(update.current_values[f]) : "(empty)"}
              </span>
              <span className="text-slate-600">→</span>
              <span className="text-emerald-400">{String(update.changes[f])}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <button
          onClick={onSave}
          disabled={saving}
          className="px-4 py-2 rounded-lg bg-blue-700 hover:bg-blue-600 disabled:opacity-50 text-sm font-medium transition-colors"
        >
          {saving ? "Saving…" : "✓ Apply changes"}
        </button>
        <button
          onClick={onReject}
          disabled={saving}
          className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-sm transition-colors"
        >
          ✗ Cancel
        </button>
      </div>
    </div>
  );
}

// ─── Image preview strip ──────────────────────────────────────────────────────

function ImagePreviewStrip({
  images,
  onRemove,
}: {
  images: { file: File; preview: string }[];
  onRemove: (index: number) => void;
}) {
  if (images.length === 0) return null;
  return (
    <div className="flex gap-2 flex-wrap mb-2">
      {images.map((img, i) => (
        <div key={i} className="relative group">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={img.preview}
            alt={img.file.name}
            className="w-16 h-16 object-cover rounded-lg border border-slate-700"
          />
          <button
            onClick={() => onRemove(i)}
            className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-700 hover:bg-red-600 text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

// ─── Main coach page ──────────────────────────────────────────────────────────

export default function CoachPage() {
  return (
    <Suspense fallback={<div className="text-slate-400 p-4">Loading coach…</div>}>
      <CoachPageInner />
    </Suspense>
  );
}

function CoachPageInner() {
  const searchParams = useSearchParams();
  const activityId = searchParams.get("activity");

  const initialGreeting = activityId
    ? `Hi! I can help you with activity #${activityId}. Would you like me to find it and suggest edits, or is there something specific you'd like to change?`
    : "Hi! I'm your climbing coach. I can help you:\n• **Log** a new activity\n• **Find & edit** past activities (you can also upload photos)\n• **Summarise** your week\n\nJust tell me what you need!";

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: initialGreeting,
    },
  ]);
  const [input, setInput] = useState(activityId ? `Find activity #${activityId}` : "");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pendingActivity, setPendingActivity] = useState<
    (Partial<Activity> & { routes?: SessionRouteCreate[] }) | null
  >(null);
  const [pendingUpdate, setPendingUpdate] = useState<PendingUpdate | null>(null);
  const [savedActivity, setSavedActivity] = useState<Activity | null>(null);
  const [pendingImages, setPendingImages] = useState<{ file: File; preview: string }[]>([]);

  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pendingActivity, pendingUpdate]);

  // ── Helpers ────────────────────────────────────────────────────────────────

  const fileToCoachImage = useCallback(async (file: File): Promise<CoachImageData> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        const base64 = result.split(",")[1];
        resolve({ content_type: file.type, data: base64 });
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const newImages = Array.from(files).map((file) => ({
      file,
      preview: URL.createObjectURL(file),
    }));
    setPendingImages((prev) => [...prev, ...newImages]);
    e.target.value = "";
  };

  const removeImage = (index: number) => {
    setPendingImages((prev) => {
      const next = [...prev];
      URL.revokeObjectURL(next[index].preview);
      next.splice(index, 1);
      return next;
    });
  };

  // ── Send message ───────────────────────────────────────────────────────────

  const send = async () => {
    const content = input.trim();
    if ((!content && pendingImages.length === 0) || loading) return;

    const userMsg: ChatMessage = { role: "user", content: content || "(image attached)" };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);
    setPendingActivity(null);
    setPendingUpdate(null);

    // Encode images
    let coachImages: CoachImageData[] = [];
    if (pendingImages.length > 0) {
      coachImages = await Promise.all(pendingImages.map((img) => fileToCoachImage(img.file)));
      setPendingImages([]);
    }

    try {
      const toSend = newMessages.filter((_, i) => i > 0);
      const res = await api.coach(toSend, coachImages);

      if (res.reply) {
        setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      }
      if (res.pending_activity && res.needs_confirmation) {
        setPendingActivity(res.pending_activity);
      }
      if (res.pending_update && res.needs_confirmation) {
        setPendingUpdate(res.pending_update);
      }
    } catch (e: unknown) {
      const errorMsg = e instanceof Error ? e.message : "Unknown error";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${errorMsg}. Make sure the backend is running.` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // ── Save new activity ──────────────────────────────────────────────────────

  const handleSaveActivity = async () => {
    if (!pendingActivity) return;
    setSaving(true);
    try {
      const saved = await api.activities.create(pendingActivity);
      setSavedActivity(saved);
      setPendingActivity(null);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `✓ Saved! Activity logged as "${saved.title}".` },
      ]);
    } catch (e: unknown) {
      const errorMsg = e instanceof Error ? e.message : "Unknown error";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Failed to save: ${errorMsg}` },
      ]);
    } finally {
      setSaving(false);
    }
  };

  const handleRejectActivity = () => {
    setPendingActivity(null);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: "That's not quite right — let me correct it." },
    ]);
  };

  // ── Apply activity update ──────────────────────────────────────────────────

  const handleApplyUpdate = async () => {
    if (!pendingUpdate) return;
    setSaving(true);
    try {
      const updated = await api.activities.update(
        pendingUpdate.activity_id,
        pendingUpdate.changes as Partial<Activity>,
      );
      setPendingUpdate(null);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `✓ Updated "${updated.title}". `,
        },
      ]);
    } catch (e: unknown) {
      const errorMsg = e instanceof Error ? e.message : "Unknown error";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Failed to update: ${errorMsg}` },
      ]);
    } finally {
      setSaving(false);
    }
  };

  const handleRejectUpdate = () => {
    setPendingUpdate(null);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: "Never mind, don't apply those changes." },
    ]);
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-2xl mx-auto flex flex-col h-[calc(100vh-12rem)]">
      <h1 className="text-2xl font-bold text-slate-100 mb-1">Coach</h1>
      <p className="text-sm text-slate-500 mb-4">Log activities, find &amp; edit sessions, or get a weekly summary.</p>

      {savedActivity && (
        <div className="mb-4 p-4 rounded-xl border border-emerald-700 bg-emerald-950/40">
          <p className="text-emerald-300 font-medium mb-1">✓ Activity saved!</p>
          <p className="text-sm text-slate-300">{savedActivity.title}</p>
          <Link
            href={`/activities/${savedActivity.id}`}
            className="text-xs text-emerald-400 hover:underline mt-1 inline-block"
          >
            View activity →
          </Link>
        </div>
      )}

      {/* Message list */}
      <div className="flex-1 overflow-y-auto space-y-3 mb-4 pr-1">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-emerald-700 text-white rounded-br-sm"
                  : "bg-slate-800 text-slate-100 rounded-bl-sm"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}

        {pendingActivity && (
          <div className="flex justify-start">
            <div className="w-full max-w-[92%]">
              <ActivityProposal
                data={pendingActivity}
                onSave={handleSaveActivity}
                onReject={handleRejectActivity}
                saving={saving}
              />
            </div>
          </div>
        )}

        {pendingUpdate && (
          <div className="flex justify-start">
            <div className="w-full max-w-[92%]">
              <UpdateProposal
                update={pendingUpdate}
                onSave={handleApplyUpdate}
                onReject={handleRejectUpdate}
                saving={saving}
              />
            </div>
          </div>
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 text-slate-400 rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm">
              Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="space-y-2">
        <ImagePreviewStrip images={pendingImages} onRemove={removeImage} />

        <div className="flex gap-2 items-end">
          {/* Image upload button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={loading || saving}
            title="Attach photo"
            className="p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-500 disabled:opacity-40 transition-colors shrink-0"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={handleFileSelect}
          />

          <textarea
            ref={textareaRef}
            rows={1}
            className="flex-1 rounded-xl bg-slate-800 border border-slate-700 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-600 resize-none"
            placeholder="Log an activity, find a session, ask for a summary…"
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              // Auto-grow
              e.target.style.height = "auto";
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={loading || saving}
          />

          <button
            onClick={send}
            disabled={loading || saving || (!input.trim() && pendingImages.length === 0)}
            className="px-4 py-2.5 rounded-xl bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-medium transition-colors shrink-0"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
