"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import BackendStatus from "@/components/BackendStatus";

const NAV = [
  { href: "/", label: "Timeline", icon: "▦" },
  { href: "/live", label: "Live", icon: "◉" },
  { href: "/settings", label: "Settings", icon: "⚙" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      {/* Top bar on mobile, sidebar on desktop */}
      <aside className="flex shrink-0 flex-col border-b border-zinc-800 bg-zinc-900/60 lg:w-56 lg:border-b-0 lg:border-r">
        <div className="flex items-center gap-2 px-4 py-4 lg:px-5 lg:py-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15 text-emerald-400">
            <span className="text-sm">◉</span>
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight">Watchtower</div>
            <div className="hidden text-[11px] text-zinc-500 sm:block">Motion recorder</div>
          </div>
        </div>

        {/* Horizontal nav on mobile, vertical on desktop */}
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:mt-2 lg:flex-col lg:pb-0">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
                  active
                    ? "bg-zinc-800 text-zinc-50"
                    : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"
                }`}
              >
                <span className="w-4 text-center">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
          <button
            onClick={logout}
            className="flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm text-zinc-400 transition-colors hover:bg-zinc-800/60 hover:text-zinc-200 lg:underline lg:underline-offset-4"
          >
            <span className="w-4 text-center">⎋</span>
            Log out
          </button>
        </nav>

        <div className="mt-auto hidden border-t border-zinc-800 px-5 py-4 text-[11px] text-zinc-600 lg:block">
          Local-first · Private by default
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <BackendStatus />
        {children}
      </main>
    </div>
  );
}