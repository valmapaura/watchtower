"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Icon from "@/components/Icon";
import Spinner from "@/components/Spinner";

/**
 * Guides the user through installing the AI object-detection package.
 * Shown when a camera uses "Smart" detection but the package isn't installed.
 * Explains in plain language and offers a one-click install.
 */
export default function YoloSetup() {
  const [installed, setInstalled] = useState<boolean | null>(null);
  const [installing, setInstalling] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const check = async () => {
    try {
      const res = await api.detectionStatus();
      setInstalled(res.installed);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't check AI support");
    }
  };

  useEffect(() => {
    let cancelled = false;
    api
      .detectionStatus()
      .then((res) => {
        if (!cancelled) setInstalled(res.installed);
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Couldn't check AI support");
      });
    // Poll while installing so the UI updates when it finishes.
    const id = setInterval(() => {
      if (installing) check();
    }, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [installing]);

  const handleInstall = async () => {
    setInstalling(true);
    setError(null);
    setMessage("Downloading the AI package… this can take a few minutes.");
    try {
      const res = await api.installDetection();
      if (res.installed) {
        setInstalled(true);
        setMessage("AI support is ready!");
        setInstalling(false);
      } else {
        setMessage(res.message);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't start the install");
      setInstalling(false);
    }
  };

  if (installed === null) return null;
  if (installed) return null;

  return (
    <div className="mt-4 rounded-lg border border-amber-900/50 bg-amber-950/40 p-4">
      <div className="flex items-start gap-3">
        <Icon name="sparkles" className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
        <div className="flex-1">
          <p className="text-sm font-medium text-amber-200">
            Smart detection needs a one-time download
          </p>
          <p className="mt-1 text-xs text-amber-200/80">
            To recognise people, vehicles, and animals, Watchtower needs to
            download a small AI helper (~2GB). It&apos;s free and only needs to
            be done once.
          </p>
          {message && <p className="mt-2 text-xs text-amber-300">{message}</p>}
          {error && (
            <p className="mt-2 text-xs text-red-300">{error}</p>
          )}
          {!installing && (
            <button
              onClick={handleInstall}
              className="mt-3 flex items-center gap-1.5 rounded-lg bg-emerald-500 px-3 py-1.5 text-sm font-medium text-zinc-950 transition-colors hover:bg-emerald-400"
            >
              <Icon name="download" className="h-4 w-4" />
              Download AI support
            </button>
          )}
          {installing && (
            <div className="mt-3 flex items-center gap-2 text-sm text-amber-300">
              <Spinner className="h-4 w-4" />
              Downloading… this may take a few minutes.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}