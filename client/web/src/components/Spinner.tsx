"use client";

/**
 * A small spinner for inline loading states (buttons, small actions).
 * Use BouncingDots for larger "we're working" moments, and this for
 * compact in-button feedback.
 */
export default function Spinner({
  className = "h-4 w-4",
  label,
}: {
  className?: string;
  label?: string;
}) {
  return (
    <span className="inline-flex items-center gap-2">
      {label && <span className="text-sm text-zinc-400">{label}</span>}
      <svg
        viewBox="0 0 24 24"
        fill="none"
        className={`animate-spin ${className}`}
        aria-hidden="true"
      >
        <circle
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="3"
          className="opacity-25"
        />
        <path
          d="M12 2a10 10 0 0 1 10 10"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          className="text-emerald-400"
        />
      </svg>
    </span>
  );
}