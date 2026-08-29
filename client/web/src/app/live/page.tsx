"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, type LiveCamera } from "@/lib/api";

export default function LivePage() {
  const [cameras, setCameras] = useState<LiveCamera[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .listLiveCameras()
      .then((data) => {
        if (!cancelled) {
          setCameras(data);
          if (data.length > 0) setSelected(data[0].name);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load cameras");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Shell>
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-8 sm:py-8">
        <header className="mb-6 flex flex-col gap-3 sm:mb-8 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Live</h1>
            <p className="mt-1 text-sm text-zinc-500">
              Watch your cameras in real time.
            </p>
          </div>
          {cameras.length > 1 && (
            <div className="flex flex-wrap gap-2">
              {cameras.map((cam) => (
                <button
                  key={cam.name}
                  onClick={() => setSelected(cam.name)}
                  className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                    selected === cam.name
                      ? "border-emerald-500 bg-emerald-500/15 text-emerald-300"
                      : "border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                  }`}
                >
                  {cam.name}
                </button>
              ))}
            </div>
          )}
        </header>

        {error && (
          <div className="mb-6 rounded-lg border border-red-900/50 bg-red-950/40 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {loading ? (
          <div className="aspect-video w-full animate-pulse rounded-xl bg-zinc-900" />
        ) : cameras.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800 py-24 text-center">
            <div className="text-4xl">📷</div>
            <p className="mt-4 text-sm text-zinc-400">No cameras configured</p>
            <p className="mt-1 text-xs text-zinc-600">
              Add a camera in Settings to view it live.
            </p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-zinc-800 bg-black">
            <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-2.5">
              <span className="text-sm font-medium text-zinc-200">
                {selected ?? "Camera"}
              </span>
              <span className="flex items-center gap-1.5 text-xs text-red-400">
                <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
                LIVE
              </span>
            </div>
            {selected && (
              // MJPEG streams render in a plain <img> tag — no video element needed.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={api.liveStreamUrl(selected)}
                alt={`Live feed from ${selected}`}
                className="aspect-video w-full object-contain"
              />
            )}
          </div>
        )}
      </div>
    </Shell>
  );
}