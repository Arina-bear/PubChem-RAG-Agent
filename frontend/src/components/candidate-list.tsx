"use client";

import type { InterpretationCandidate } from "@/lib/types";

export function CandidateList({
  candidates,
  recommendedIndex,
  selectedIndex,
  onSelect,
  onRun,
  isRunning,
}: {
  candidates: InterpretationCandidate[];
  recommendedIndex: number;
  selectedIndex: number | null;
  onSelect: (index: number) => void;
  onRun: () => void;
  isRunning: boolean;
}) {
  if (!candidates.length) {
    return null;
  }

  const mostLikely = Math.min(Math.max(recommendedIndex, 0), candidates.length - 1);
  const activeIndex = selectedIndex ?? mostLikely;
  const activeCandidate = candidates[activeIndex];

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--muted)]">Наиболее вероятная интерпретация</p>
        <div className="mt-3 rounded-3xl border border-[var(--border)] bg-white/90 p-4">
          <button
            className="w-full text-left"
            onClick={() => onSelect(mostLikely)}
            type="button"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-base font-semibold">{candidates[mostLikely].label}</h3>
                <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{candidates[mostLikely].rationale}</p>
              </div>
              <span className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-medium text-[var(--accent-strong)]">
                Уверенность {Math.round(candidates[mostLikely].confidence * 100)}%
              </span>
            </div>
          </button>
        </div>
      </div>

      {candidates.length > 1 ? (
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--muted)]">Другие варианты</p>
          <div className="mt-3 space-y-3">
            {candidates.map((candidate, index) => {
              if (index === mostLikely) {
                return null;
              }

              const selected = selectedIndex === index;
              return (
                <button
                  className={`w-full rounded-3xl border p-4 text-left transition ${
                    selected
                      ? "border-[var(--accent)] bg-[var(--accent-soft)]/60"
                      : "border-[var(--border)] bg-white/80 hover:border-[var(--accent)]/45"
                  }`}
                  key={`${candidate.label}-${index}`}
                  onClick={() => onSelect(index)}
                  type="button"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="text-sm font-semibold">{candidate.label}</h3>
                      <p className="mt-1 text-sm leading-6 text-[var(--muted)]">{candidate.rationale}</p>
                    </div>
                    <span className="rounded-full border border-[var(--border)] px-3 py-1 text-xs font-medium">
                      {Math.round(candidate.confidence * 100)}%
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <button
          className="rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-70"
          disabled={selectedIndex === null || isRunning}
          onClick={onRun}
          type="button"
        >
          {isRunning ? "Запускаю выбранный запрос..." : "Выполнить выбранный запрос"}
        </button>
        <span className="text-sm text-[var(--muted)]">
          {activeIndex === mostLikely
            ? "Сейчас будет выполнен наиболее вероятный вариант через backend."
            : `Сейчас будет выполнен выбранный вариант: ${activeCandidate.label}.`}
        </span>
      </div>
    </div>
  );
}
