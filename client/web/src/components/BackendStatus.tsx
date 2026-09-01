"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Icon from "@/components/Icon";
import Spinner from "@/components/Spinner";

type BackendState = "online" | "offline" | "starting" | "error";

// The desktop app exposes this via the preload script.
interface WatchtowerBridge {
  isDesktop: boolean;
  startBackend: () => Promise<{ ok: boolean; message: string }>;
  onBackendStatus: (
    cb: (data: { message: string; state: string }) => void
  ) => () => void;
}

function bridge(): WatchtowerBridge | undefined {
  if (typeof window === "undefined") return undefined;
  return (window as unknown as { watchtower?: WatchtowerBridge }).watchtower;
}

/**
 * Shows a friendly banner when the Watchtower service isn't reachable.
 * In the desktop app, it offers a "Start it for me" button and shows live
 * status from the main process. In a browser, it explains simply what to do.
 */
export default function BackendStatus() {
  const [state, setState] = useState<BackendState>("online");
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  // Is this running inside the Electron desktop app?
  const isDesktop = bridge()?.isDesktop ?? false;

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      api
        .health()
        .then(() => {
          if (!cancelled) {
            setState("online");
            setStatusMsg(null);
          }
        })
        .catch(() => {
          if (!cancelled) setState("offline");
        });
    };
    check();
    const id = setInterval(check, 10000); // re-check every 10s
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  // Listen for backend status from the desktop app's main process.
  useEffect(() => {
    const wt = bridge();
    if (!wt?.onBackendStatus) return;
    const unsub = wt.onBackendStatus((data) => {
      setStatusMsg(data.message);
      if (data.state === "running") {
        setState("online");
        setStarting(false);
      } else if (data.state === "error") {
        setState("error");
        setStarting(false);
      } else {
        setState("starting");
      }
    });
    return unsub;
  }, [isDesktop]);

  const handleStart = async () => {
    setStarting(true);
    setState("starting");
    setStatusMsg("Starting the Watchtower service…");
    try {
      const wt = bridge();
      if (wt?.startBackend) {
        await wt.startBackend();
      } else {
        // In a browser, we can't start it — just show a message.
        setStatusMsg(
          "Open the Watchtower app on your computer to start the service."
        );
        setStarting(false);
      }
    } catch {
      setStatusMsg("Couldn't start the service. Please restart the app.");
      setStarting(false);
    }
  };

  if (state === "online") return null;

  const isStarting = state === "starting" || starting;

  return (
    <div className="flex flex-col items-center gap-2 border-b border-amber-900/50 bg-amber-950/40 px-4 py-3 text-center sm:flex-row sm:justify-center sm:gap-3">
      <span className="flex items-center gap-2 text-sm text-amber-300">
        <Icon name="plug" className="h-4 w-4 shrink-0" />
        {statusMsg ||
          (isStarting
            ? "Starting the Watchtower service…"
            : "The Watchtower service isn't running.")}
      </span>
      {isDesktop && !isStarting && (
        <button
          onClick={handleStart}
          className="flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3 py-1.5 text-sm font-medium text-zinc-950 transition-colors hover:bg-emerald-400"
        >
          <Icon name="play" className="h-3.5 w-3.5" />
          Start it for me
        </button>
      )}
      {isStarting && <Spinner className="h-4 w-4 text-amber-300" />}
    </div>
  );
}