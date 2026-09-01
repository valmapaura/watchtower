"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import Shell from "@/components/Shell";
import AuthGate from "@/components/AuthGate";
import Icon from "@/components/Icon";
import PageTransition from "@/components/PageTransition";
import { useAuth } from "@/lib/auth";
import { api, type Clip } from "@/lib/api";
import { formatDate, formatDuration, motionLabel } from "@/lib/format";

export default function Home() {
  const { authenticated } = useAuth();
  const [clips, setClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [category, setCategory] = useState<string>("all");
  const [source, setSource] = useState<string>("all");

  useEffect(() => {
    if (!authenticated) return;
    let cancelled = false;
    api
      .listClips()
      .then((data) => {
        if (!cancelled) setClips(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load clips");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey, authenticated]);

  const categories = Array.from(new Set(clips.map((c) => c.category))).sort();
  const filtered =
    category === "all" ? clips : clips.filter((c) => c.category === category);
  const sourceFiltered =
    source === "all"
      ? filtered
      : filtered.filter((c) =>
          source === "manual"
            ? c.recorded_by === "manual-live-record"
            : c.recorded_by !== "manual-live-record",
        );

  const handleDelete = async (clip: Clip) => {
    if (!confirm(`Delete clip from ${clip.camera}?`)) return;
    try {
      await api.deleteClip(clip.filename);
      setClips((prev) => prev.filter((c) => c.filename !== clip.filename));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const handleDeleteAll = async () => {
    if (clips.length === 0) return;
    const count = filtered.length;
    if (
      !confirm(
        `Delete ALL ${count} recording${count === 1 ? "" : "s"}?\n\nThis permanently removes every clip from your library and can't be undone.`,
      )
    ) {
      return;
    }
    // Second confirmation for safety — this is destructive.
    if (!confirm("Are you absolutely sure? This can't be undone.")) return;
    try {
      const res = await api.deleteAllClips();
      setClips([]);
      setError(null);
      setReloadKey((k) => k + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete all failed");
    }
  };

  return (
    <AuthGate>
      <Shell>
        <PageTransition>
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-8 sm:py-8">
        <header className="mb-6 flex flex-col gap-3 sm:mb-8 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
              <Icon name="timeline" className="h-6 w-6 text-emerald-400" />
              Timeline
            </h1>
            <p className="mt-1 text-sm text-zinc-500">
              {sourceFiltered.length} recorded clip{sourceFiltered.length === 1 ? "" : "s"}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm text-zinc-300 outline-none focus:border-emerald-500"
            >
              <option value="all">All recordings</option>
              <option value="motion">Motion detected</option>
              <option value="manual">Manually recorded</option>
            </select>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm text-zinc-300 outline-none focus:border-emerald-500"
            >
              <option value="all">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <button
              onClick={() => setReloadKey((k) => k + 1)}
              className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-300 transition-colors hover:bg-zinc-800"
            >
              <Icon name="refresh" className="h-3.5 w-3.5" />
              Refresh
            </button>
            {filtered.length > 0 && (
              <button
                onClick={handleDeleteAll}
                className="flex items-center gap-1.5 rounded-lg border border-red-900/60 px-3 py-1.5 text-sm text-red-300 transition-colors hover:bg-red-950/40"
              >
                <Icon name="trash" className="h-3.5 w-3.5" />
                Delete all
              </button>
            )}
          </div>
        </header>

        {error && (
          <div className="mb-6 rounded-lg border border-red-900/50 bg-red-950/40 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-48 animate-pulse rounded-xl bg-zinc-900" />
            ))}
          </div>
        ) : sourceFiltered.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800 py-24 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-900 text-zinc-500">
              <Icon name="film" className="h-8 w-8" />
            </div>
            <p className="mt-4 text-sm font-medium text-zinc-300">
              {category === "all" && source === "all"
                ? "No recordings yet"
                : "No matching recordings"}
            </p>
            <p className="mt-1 max-w-sm text-xs text-zinc-600">
              When your camera spots movement, the clip will show up here
              automatically. You can also watch your cameras live from the{" "}
              <span className="text-zinc-400">Live</span> tab.
            </p>
          </div>
        ) : (
          <motion.div
            layout
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
          >
            <AnimatePresence>
              {sourceFiltered.map((clip, i) => (
                <motion.div
                  key={clip.filename}
                  layout
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.25, delay: i * 0.04 }}
                >
                  <ClipCard
                    clip={clip}
                    playing={playing === clip.filename}
                    onPlay={() => setPlaying(clip.filename)}
                    onDelete={() => handleDelete(clip)}
                  />
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
        </PageTransition>
      </Shell>
    </AuthGate>
  );
}

function ClipCard({
  clip,
  playing,
  onPlay,
  onDelete,
}: {
  clip: Clip;
  playing: boolean;
  onPlay: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="group overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/60 transition-colors hover:border-zinc-700">
      <div className="relative aspect-video bg-black">
        {playing ? (
          <video
            src={api.streamUrl(clip.filename)}
            controls
            autoPlay
            className="h-full w-full"
          />
        ) : (
          <button
            onClick={onPlay}
            className="flex h-full w-full items-center justify-center bg-zinc-950"
            aria-label={`Play ${clip.filename}`}
          >
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/90 text-zinc-950 shadow-lg transition-transform group-hover:scale-105">
              <Icon name="play" className="ml-0.5 h-6 w-6" />
            </div>
          </button>
        )}
      </div>

      <div className="p-4">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5 text-sm font-medium text-zinc-200">
            <Icon name="camera" className="h-3.5 w-3.5 text-zinc-500" />
            {clip.camera}
          </span>
          <div className="flex items-center gap-2">
            <SourceBadge recordedBy={clip.recorded_by} />
            {clip.category !== "motion" && (
              <CategoryBadge category={clip.category} />
            )}
            {clip.motion_score > 0 && (
              <MotionBadge score={clip.motion_score} />
            )}
          </div>
        </div>
        <div className="mt-1 flex items-center gap-1.5 text-xs text-zinc-500">
          <Icon name="clock" className="h-3 w-3" />
          {formatDate(clip.start_utc)}
        </div>
        <div className="mt-3 flex items-center justify-between text-xs">
          <span className="flex items-center gap-1.5 text-zinc-400">
            <Icon name="video" className="h-3.5 w-3.5" />
            {formatDuration(clip.duration_s)}
          </span>
          <div className="flex gap-2">
            <a
              href={api.downloadUrl(clip.filename)}
              download
              className="flex items-center gap-1.5 rounded-md border border-zinc-700 px-2 py-1 text-zinc-300 transition-colors hover:bg-zinc-800"
            >
              <Icon name="download" className="h-3.5 w-3.5" />
              Download
            </a>
            <button
              onClick={onDelete}
              className="flex items-center gap-1.5 rounded-md border border-zinc-700 px-2 py-1 text-zinc-400 transition-colors hover:border-red-900 hover:bg-red-950/40 hover:text-red-300"
            >
              <Icon name="trash" className="h-3.5 w-3.5" />
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function MotionBadge({ score }: { score: number }) {
  const label = motionLabel(score);
  const color =
    label === "High"
      ? "bg-red-500/15 text-red-400"
      : label === "Medium"
        ? "bg-amber-500/15 text-amber-400"
        : "bg-zinc-700/40 text-zinc-400";
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${color}`}>
      {label}
    </span>
  );
}

function CategoryBadge({ category }: { category: string }) {
  const color =
    category === "person"
      ? "bg-sky-500/15 text-sky-400"
      : category === "vehicle"
        ? "bg-orange-500/15 text-orange-400"
        : category === "animal"
          ? "bg-emerald-500/15 text-emerald-400"
          : "bg-zinc-700/40 text-zinc-400";
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ${color}`}>
      {category}
    </span>
  );
}

function SourceBadge({ recordedBy }: { recordedBy: string }) {
  const isManual = recordedBy === "manual-live-record";
  return (
    <span
      className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${
        isManual
          ? "bg-violet-500/15 text-violet-300"
          : "bg-emerald-500/15 text-emerald-300"
      }`}
    >
      <Icon name={isManual ? "record" : "sparkles"} className="h-3 w-3" />
      {isManual ? "Manual" : "Motion"}
    </span>
  );
}
