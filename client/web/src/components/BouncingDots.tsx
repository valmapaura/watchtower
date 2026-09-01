"use client";

/**
 * A bouncing-dots loading indicator. Shows the app is working, not frozen.
 */
export default function BouncingDots({
  label,
  className = "",
}: {
  label?: string;
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      {label && <span className="text-sm text-zinc-400">{label}</span>}
      <span className="inline-flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 animate-bounce rounded-full bg-emerald-400"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </span>
    </span>
  );
}