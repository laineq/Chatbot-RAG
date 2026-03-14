"use client";

import type { FeedbackRating } from "@/types/chat";

type FeedbackButtonsProps = {
  currentRating?: FeedbackRating;
  disabled?: boolean;
  onRate: (rating: FeedbackRating) => void;
};

const options: Array<{ rating: FeedbackRating; label: string }> = [
  { rating: "up", label: "Useful" },
  { rating: "down", label: "Needs work" },
];

export function FeedbackButtons({
  currentRating,
  disabled = false,
  onRate,
}: FeedbackButtonsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => {
        const active = currentRating === option.rating;
        return (
          <button
            key={option.rating}
            type="button"
            onClick={() => onRate(option.rating)}
            disabled={disabled}
            className={`rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] transition ${
              active
                ? "border-[color:var(--accent-strong)] bg-[color:var(--accent-strong)] text-white"
                : "border-black/10 bg-white/70 text-[color:var(--ink-soft)] hover:border-[color:var(--accent)]"
            } ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

