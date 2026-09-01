"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type ServerStatus, type StorageInfo } from "@/lib/api";
import InfoTip from "@/components/InfoTip";
import Icon from "@/components/Icon";
import Spinner from "@/components/Spinner";

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1
  );
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

/**
 * "Server" panel for Settings: shows whether the service is running, how long
 * it's been up, and how much disk space the recordings are using (with a
 * per-camera breakdown). Also offers a "Restart server" button.
 */
export default function ServerManager() {
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [storage, setStorage] = useState<StorageInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [restarting, setRestarting] = useState(false);
  const [restartMsg, setRestartMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [s, st] = await Promise.all([api.serverStatus(), api.storageInfo()]);
      setStatus(s);
      setStorage(st);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't reach the server");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.serverStatus(), api.storageInfo()])
      .then(([s, st]) => {
        if (cancelled) return;
        setStatus(s);
        setStorage(st);
        setError(null);
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Couldn't reach the server");
      });
    const id = setInterval(() => {
      load();
    }, 10000); // refresh every 10s
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [load]);

  const handleRestart = async () => {
    if (!confirm("Restart the Watchtower service? It'll be back in a few seconds."))
      return;
    setRestarting(true);
    setRestartMsg(null);
    try {
      await api.restartServer();
      setRestartMsg("Restarting… the page will reconnect shortly.");
      // The backend will briefly go offline; poll until it's back.
      const started = Date.now();
      const poll = setInterval(async () => {
        try {
          await api.health();
          clearInterval(poll);
          setRestarting(false);
          setRestartMsg("Server restarted ✓");
          setTimeout(() => setRestartMsg(null), 3000);
          load();
        } catch {
          if (Date.now() - started > 30000) {
            clearInterval(poll);
            setRestarting(false);
            setRestartMsg("Couldn't reconnect. Is the launcher window still open?");
          }
        }
      }, 1500);
    } catch (e) {
      setRestarting(false);
      setRestartMsg(e instanceof Error ? e.message : "Restart failed");
    }
  };

  const pct = storage && storage.cap_bytes > 0
    ? Math.min(100, (storage.total_bytes / storage.cap_bytes) * 100)
    : 0;

  return (
    <section className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
          <Icon name="server" className="h-4 w-4 text-emerald-400" />
          Server
        </h2>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
            status
              ? "bg-emerald-500/15 text-emerald-300"
              : "bg-red-500/15 text-red-300"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              status ? "bg-emerald-400" : "bg-red-400"
            }`}
          />
          {status ? "Running" : "Offline"}
        </span>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-900/50 bg-red-950/40 px-4 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      {status && (
        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="Version" value={status.version} />
          <Stat label="Uptime" value={formatUptime(status.uptime_s)} />
          <Stat label="Cameras" value={String(status.camera_count)} />
          <Stat label="Web port" value={String(status.web_port)} />
        </div>
      )}

      {/* Storage */}
      {storage && (
        <div className="mt-6">
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-1.5 text-sm text-zinc-400">
              <Icon name="hardDrive" className="h-4 w-4 text-zinc-500" />
              Recordings on disk
              <InfoTip title="Storage used">
                How much space your recordings are using, and how it compares to
                your storage limit. Old clips are deleted automatically to stay
                under the limit.
              </InfoTip>
            </label>
            <span className="text-sm text-zinc-300">
              {formatBytes(storage.total_bytes)}
              {storage.cap_bytes > 0 && (
                <span className="text-zinc-500"> / {formatBytes(storage.cap_bytes)}</span>
              )}
            </span>
          </div>

          <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-zinc-800">
            <div
              className={`h-full rounded-full transition-all ${
                pct > 90 ? "bg-red-500" : pct > 70 ? "bg-amber-500" : "bg-emerald-500"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="mt-1 text-xs text-zinc-500">
            {storage.clip_count} clip{storage.clip_count === 1 ? "" : "s"}
            {storage.cap_bytes > 0 && ` · ${pct.toFixed(0)}% of your limit`}
          </div>

          {storage.per_camera.length > 0 && (
            <div className="mt-4 space-y-2">
              {storage.per_camera.map((c) => (
                <div
                  key={c.camera}
                  className="flex items-center justify-between rounded-lg bg-zinc-950/60 px-3 py-2"
                >
                  <span className="flex items-center gap-1.5 text-sm text-zinc-300">
                    <Icon name="camera" className="h-3.5 w-3.5 text-zinc-500" />
                    {c.camera}
                  </span>
                  <span className="text-sm text-zinc-500">{formatBytes(c.bytes)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Restart */}
      <div className="mt-6 flex items-center gap-3">
        <button
          onClick={handleRestart}
          disabled={restarting}
          className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-800 disabled:opacity-50"
        >
          {restarting ? (
            <Spinner className="h-4 w-4" label="Restarting…" />
          ) : (
            <>
              <Icon name="refresh" className="h-4 w-4" />
              Restart server
            </>
          )}
        </button>
        {restartMsg && <span className="text-sm text-zinc-400">{restartMsg}</span>}
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-0.5 text-sm font-medium text-zinc-200">{value}</div>
    </div>
  );
}
