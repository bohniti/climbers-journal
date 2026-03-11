"use client";

import { useCallback, useRef, useState } from "react";
import { api, ActivityPhoto } from "@/lib/api";

interface Props {
  activityId: number;
  photos: ActivityPhoto[];
  onPhotosChange: (photos: ActivityPhoto[]) => void;
  editable: boolean;
}

export default function PhotoGallery({ activityId, photos, onPhotosChange, editable }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [lightboxId, setLightboxId] = useState<number | null>(null);

  // ── Upload handler ──────────────────────────────────────────────────────
  const handleUpload = useCallback(
    async (files: FileList | File[]) => {
      if (!files.length) return;
      setUploading(true);
      try {
        const created = await api.photos.upload(activityId, files);
        onPhotosChange([...photos, ...created]);
      } catch (e) {
        console.error("Upload failed:", e);
      } finally {
        setUploading(false);
      }
    },
    [activityId, photos, onPhotosChange]
  );

  // ── Delete handler ──────────────────────────────────────────────────────
  const handleDelete = useCallback(
    async (photoId: number) => {
      try {
        await api.photos.delete(photoId);
        onPhotosChange(photos.filter((p) => p.id !== photoId));
        if (lightboxId === photoId) setLightboxId(null);
      } catch (e) {
        console.error("Delete failed:", e);
      }
    },
    [photos, onPhotosChange, lightboxId]
  );

  // ── Drag & drop ────────────────────────────────────────────────────────
  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };
  const onDragLeave = () => setDragOver(false);
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) handleUpload(e.dataTransfer.files);
  };

  // Don't render anything if no photos and not editable
  if (!editable && photos.length === 0) return null;

  const lightboxPhoto = lightboxId != null ? photos.find((p) => p.id === lightboxId) : null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
        Photos {photos.length > 0 && <span className="text-slate-500">({photos.length})</span>}
      </h3>

      {/* Upload zone (edit mode only) */}
      {editable && (
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer ${
            dragOver
              ? "border-emerald-500 bg-emerald-500/10"
              : "border-slate-700 hover:border-slate-600"
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => {
              if (e.target.files) handleUpload(e.target.files);
              e.target.value = "";
            }}
          />
          {uploading ? (
            <p className="text-slate-400 text-sm">Uploading…</p>
          ) : (
            <div>
              <p className="text-slate-400 text-sm">Drop photos here or click to upload</p>
              <p className="text-slate-600 text-xs mt-1">JPEG, PNG, WebP — max 15 MB each</p>
            </div>
          )}
        </div>
      )}

      {/* Photo grid */}
      {photos.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {photos.map((photo) => (
            <div key={photo.id} className="relative group">
              <button
                onClick={() => setLightboxId(photo.id)}
                className="block w-full aspect-square rounded-lg overflow-hidden border border-slate-700 hover:border-slate-500 transition-colors"
              >
                <img
                  src={api.photos.fileUrl(photo.id)}
                  alt={photo.original_name}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              </button>

              {/* EXIF badges */}
              <div className="absolute bottom-1 left-1 flex gap-1">
                {photo.exif_lat && photo.exif_lon && (
                  <span className="bg-slate-900/80 text-emerald-400 text-[10px] px-1.5 py-0.5 rounded" title={`${photo.exif_lat}, ${photo.exif_lon}`}>
                    📍
                  </span>
                )}
                {photo.exif_date && (
                  <span className="bg-slate-900/80 text-slate-300 text-[10px] px-1.5 py-0.5 rounded" title={photo.exif_date}>
                    📅
                  </span>
                )}
              </div>

              {/* Delete button (edit mode) */}
              {editable && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(photo.id);
                  }}
                  className="absolute top-1 right-1 bg-red-900/80 hover:bg-red-800 text-white text-xs w-6 h-6 rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                  title="Delete photo"
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Lightbox modal */}
      {lightboxPhoto && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setLightboxId(null)}
        >
          <button
            className="absolute top-4 right-4 text-white text-2xl hover:text-slate-300 z-10"
            onClick={() => setLightboxId(null)}
          >
            ✕
          </button>
          <img
            src={api.photos.fileUrl(lightboxPhoto.id)}
            alt={lightboxPhoto.original_name}
            className="max-w-full max-h-full object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-sm text-slate-400 bg-slate-900/80 px-3 py-1 rounded-lg">
            {lightboxPhoto.original_name}
            {lightboxPhoto.exif_lat && lightboxPhoto.exif_lon && (
              <span className="ml-3 text-emerald-400">
                📍 {lightboxPhoto.exif_lat.toFixed(4)}, {lightboxPhoto.exif_lon.toFixed(4)}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
