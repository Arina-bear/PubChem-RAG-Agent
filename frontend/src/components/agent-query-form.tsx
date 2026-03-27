"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { CandidateList } from "@/components/candidate-list";
import type { InterpretResponseEnvelope, ManualQuerySpec } from "@/lib/types";

const interpretSchema = z.object({
  text: z.string().trim().min(1, "Опишите, что вы хотите найти."),
});

type InterpretFormValues = z.infer<typeof interpretSchema>;

export function AgentQueryForm({
  isLoading,
  interpretResult,
  onInterpret,
  onRunCandidate,
  isRunningCandidate,
}: {
  isLoading: boolean;
  interpretResult: InterpretResponseEnvelope | null;
  onInterpret: (text: string) => void;
  onRunCandidate: (query: ManualQuerySpec) => void;
  isRunningCandidate: boolean;
}) {
  const form = useForm<InterpretFormValues>({
    resolver: zodResolver(interpretSchema),
    defaultValues: {
      text: "найди aspirin",
    },
  });

  const [selectedCandidateIndex, setSelectedCandidateIndex] = useState<number | null>(0);
  const normalized = interpretResult?.normalized ?? null;

  useEffect(() => {
    setSelectedCandidateIndex(normalized?.recommended_candidate_index ?? (normalized?.candidates.length ? 0 : null));
  }, [normalized]);

  return (
    <div className="glass-panel rounded-[28px] p-6 panel-strong">
      <div className="mb-6">
        <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--muted)]">Агент</p>
        <h2 className="mt-2 text-2xl font-semibold">Интерпретатор запроса</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
          Этот режим не отвечает за вас и не делает запрос молча. Он переводит текст в один или несколько
          структурированных запросов, а затем ждёт явного подтверждения.
        </p>
      </div>

      <form className="space-y-4" onSubmit={form.handleSubmit((values) => onInterpret(values.text))}>
        <label className="space-y-2">
          <span className="text-sm font-medium">Опишите, что нужно найти</span>
          <textarea
            className="min-h-[140px] w-full rounded-3xl border border-[var(--border)] bg-white/80 px-4 py-4 text-sm leading-6 outline-none"
            placeholder="Например: найди aspirin, CID 2244 или SMILES CC(=O)OC1=CC=CC=C1C(=O)O"
            {...form.register("text")}
          />
        </label>
        {form.formState.errors.text ? <p className="text-sm text-[var(--warning)]">{form.formState.errors.text.message}</p> : null}

        <button
          className="rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-70"
          disabled={isLoading}
          type="submit"
        >
          {isLoading ? "Интерпретирую..." : "Разобрать запрос"}
        </button>
      </form>

      {normalized ? (
        <div className="mt-8 space-y-6">
          <div className="data-grid">
            <div className="rounded-3xl border border-[var(--border)] bg-white/90 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Нужно подтверждение</p>
              <p className="mt-3 text-xl font-semibold">{normalized.needs_confirmation ? "Да" : "Нет"}</p>
            </div>
            <div className="rounded-3xl border border-[var(--border)] bg-white/90 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Уверенность интерпретации</p>
              <p className="mt-3 text-xl font-semibold">{Math.round(normalized.confidence * 100)}%</p>
            </div>
          </div>

          <CandidateList
            candidates={normalized.candidates}
            isRunning={isRunningCandidate}
            onRun={() => {
              if (selectedCandidateIndex === null) {
                return;
              }
              const candidate = normalized.candidates[selectedCandidateIndex];
              if (candidate) {
                onRunCandidate(candidate.query);
              }
            }}
            onSelect={setSelectedCandidateIndex}
            recommendedIndex={normalized.recommended_candidate_index ?? 0}
            selectedIndex={
              normalized.candidates.length
                ? selectedCandidateIndex ?? normalized.recommended_candidate_index ?? 0
                : null
            }
          />

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-3xl border border-[var(--border)] bg-white/90 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Допущения</p>
              <div className="mt-3 space-y-2 text-sm leading-6 text-[var(--muted)]">
                {normalized.assumptions.length ? (
                  normalized.assumptions.map((item) => <p key={item}>{item}</p>)
                ) : (
                  <p>Допущений не понадобилось.</p>
                )}
              </div>
            </div>
            <div className="rounded-3xl border border-[var(--border)] bg-white/90 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Неясности и предупреждения</p>
              <div className="mt-3 space-y-2 text-sm leading-6 text-[var(--muted)]">
                {[...normalized.ambiguities, ...normalized.warnings].length ? (
                  [...normalized.ambiguities, ...normalized.warnings].map((item) => <p key={item}>{item}</p>)
                ) : (
                  <p>Дополнительных неясностей не найдено.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
