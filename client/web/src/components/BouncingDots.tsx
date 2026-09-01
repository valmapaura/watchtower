"use client";

/**
 * A bouncing-dots loading indicator. Shows the app is working, not frozen.
 * Use with a label like "Testing connection…".
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
      <span className="inline-flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 animate-bounce rounded-full bg-emerald-400"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </span>
    </span>
  );
}