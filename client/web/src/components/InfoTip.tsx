"use client";

import { useState } from "react";
import Icon from "@/components/Icon";

/**
 * A small help icon that reveals a plain-language explainer.
 * Opens on hover (desktop) and on click (touch). Keeps the UI clean — the
 * explanation is hidden until the user asks for it.
 */
export default function InfoTip({
  title,
  children,
  side = "bottom",
}: {
  title: string;
  children: React.ReactNode;
  side?: "bottom" | "right" | "left";
}) {
  const [open, setOpen] = useState(false);

  const position =
    side === "right"
      ? "left-full top-1/2 -translate-y-1/2 ml-2"
      : side === "left"
        ? "right-full top-1/2 -translate-y-1/2 mr-2"
        : "left-0 top-6";

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label={`What does ${title} mean?`}
        className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-zinc-700/60 text-zinc-300 transition-colors hover:bg-emerald-500/20 hover:text-emerald-300"
      >
        <Icon name="help" className="h-3 w-3" strokeWidth={2.5} />
      </button>
      {open && (
        <>
          {/* Click-away backdrop (touch) */}
          <button
            type="button"
            aria-label="Close"
            onClick={() => setOpen(false)}
            className="fixed inset-0 z-10 cursor-default"
          />
          <div
            className={`absolute z-20 w-64 rounded-lg border border-zinc-700 bg-zinc-900 p-3 shadow-xl ${position}`}
          >
            <div className="text-xs font-semibold text-zinc-100">{title}</div>
            <div className="mt-1.5 text-xs leading-relaxed text-zinc-400">
              {children}
            </div>
          </div>
        </>
      )}
    </span>
  );
}