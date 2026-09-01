"use client";

import { useState } from "react";
import Icon from "@/components/Icon";

/**
 * A collapsible section. Keeps advanced/optional settings hidden by default
 * so the main view stays clean and obvious for new users. Clicking the header
 * expands or collapses it.
 */
export default function Accordion({
  title,
  icon,
  children,
  defaultOpen = false,
  badge,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/60">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left transition-colors hover:bg-zinc-800/40"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2.5 text-sm font-semibold text-zinc-200">
          {icon && <span className="text-zinc-400">{icon}</span>}
          {title}
          {badge && (
            <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[11px] font-medium text-zinc-400">
              {badge}
            </span>
          )}
        </span>
        <Icon
          name="chevronDown"
          className={`h-4 w-4 shrink-0 text-zinc-500 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      {open && <div className="border-t border-zinc-800 px-5 py-4">{children}</div>}
    </div>
  );
}