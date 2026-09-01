"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Icon from "@/components/Icon";

/**
 * Shows a banner when the backend API is unreachable, so users know the
 * problem is the backend (not their camera).
 */
export default function BackendStatus() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      api
        .health()
        .then(() => {
          if (!cancelled) setOnline(true);
        })
        .catch(() => {
          if (!cancelled) setOnline(false);
        });
    };
    check();
    const id = setInterval(check, 10000); // re-check every 10s
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (online === null || online) return null;

  return (
    <div className="flex items-center justify-center gap-2 border-b border-amber-900/50 bg-amber-950/40 px-4 py-2 text-center text-sm text-amber-300">
      <Icon name="plug" className="h-4 w-4 shrink-0" />
      <span>
        The Watchtower service isn&apos;t running. Start it with{" "}
        <code className="rounded bg-amber-900/40 px-1.5 py-0.5 text-xs">
          python -m watchtower.api --config config.json
        </code>{" "}
        to view your cameras.
      </span>
    </div>
  );
}