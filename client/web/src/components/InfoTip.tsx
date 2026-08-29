"use client";

import { useState } from "react";

/**
 * A small "?" button that opens a mini explainer popover.
 * Used to translate technical settings into plain language for new users.
 */
export default function InfoTip({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-flex">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-label={`What does ${title} mean?`}
        className="ml-1.5 inline-flex h-4 w-4 items-center justify-center rounded-full bg-zinc-700/60 text-[10px] font-semibold text-zinc-300 transition-colors hover:bg-zinc-600 hover:text-white"
      >
        ?
      </button>
      {open && (
        <>
          {/* Click-away backdrop */}
          <button
            type="button"
            aria-label="Close"
            onClick={() => setOpen(false)}
            className="fixed inset-0 z-10 cursor-default"
          />
          <div className="absolute left-0 top-6 z-20 w-64 rounded-lg border border-zinc-700 bg-zinc-900 p-3 shadow-xl">
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