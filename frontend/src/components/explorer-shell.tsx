"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { AgentQueryForm } from "@/components/agent-query-form";
import { ManualQueryForm } from "@/components/manual-query-form";
import { ResultPanel } from "@/components/result-panel";
import { interpretText, runQuery } from "@/lib/api";
import type { InterpretResponseEnvelope, ManualQuerySpec, QueryResponseEnvelope } from "@/lib/types";

type ExplorerMode = "manual" | "agent";

export function ExplorerShell() {
  const [mode, setMode] = useState<ExplorerMode>("manual");
  const [queryResult, setQueryResult] = useState<QueryResponseEnvelope | null>(null);
  const [interpretResult, setInterpretResult] = useState<InterpretResponseEnvelope | null>(null);
  const [lastQuerySpec, setLastQuerySpec] = useState<ManualQuerySpec | null>(null);

  const queryMutation = useMutation({
    mutationFn: runQuery,
    onSuccess: (response) => {
      setQueryResult(response.data);
    },
  });

  const interpretMutation = useMutation({
    mutationFn: interpretText,
    onSuccess: (response) => {
      setInterpretResult(response.data);
    },
  });

  const handleManualSubmit = (spec: ManualQuerySpec) => {
    setLastQuerySpec(spec);
    queryMutation.mutate(spec);
  };

  const handleInterpret = (text: string) => {
    interpretMutation.mutate({ text });
  };

  const handleRunCandidate = (spec: ManualQuerySpec) => {
    setLastQuerySpec(spec);
    queryMutation.mutate(spec);
  };

  return (
    <main className="mx-auto max-w-[1500px] px-4 py-8 md:px-6 lg:px-8">
      <section className="mb-8 rounded-[36px] border border-[var(--border)] bg-white/70 p-6 shadow-[var(--shadow)] backdrop-blur md:p-8">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.26em] text-[var(--muted)]">PubChem Compound Explorer</p>
            <h1 className="mt-3 max-w-4xl text-4xl font-semibold leading-tight md:text-5xl">
              Поиск соединений в PubChem с ручным и агентным режимами
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-[var(--muted)] md:text-base">
              В первой версии мы держим один надёжный сценарий: ручной запрос и агент, который сначала предлагает
              структурированный запрос, а уже потом запускает его через backend. Браузер не обращается к PubChem напрямую.
            </p>
          </div>

          <div className="inline-flex rounded-full border border-[var(--border)] bg-white/90 p-1">
            <button
              className={`rounded-full px-5 py-2.5 text-sm font-medium transition ${
                mode === "manual" ? "bg-[var(--accent)] text-white" : "text-[var(--muted)]"
              }`}
              onClick={() => setMode("manual")}
              type="button"
            >
              Ручной режим
            </button>
            <button
              className={`rounded-full px-5 py-2.5 text-sm font-medium transition ${
                mode === "agent" ? "bg-[var(--accent)] text-white" : "text-[var(--muted)]"
              }`}
              onClick={() => setMode("agent")}
              type="button"
            >
              Агент
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,540px)_minmax(0,1fr)]">
        <div className="space-y-6">
          {mode === "manual" ? (
            <ManualQueryForm isLoading={queryMutation.isPending} onSubmit={handleManualSubmit} />
          ) : (
            <AgentQueryForm
              interpretResult={interpretResult}
              isLoading={interpretMutation.isPending}
              isRunningCandidate={queryMutation.isPending}
              onInterpret={handleInterpret}
              onRunCandidate={handleRunCandidate}
            />
          )}

          <section className="glass-panel rounded-[28px] p-6">
            <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--muted)]">Как это работает</p>
            <div className="mt-4 space-y-3 text-sm leading-6 text-[var(--muted)]">
              <p>Ручной режим сразу отправляет типизированный запрос.</p>
              <p>Агентный режим сначала строит варианты запроса и ждёт явного подтверждения.</p>
              <p>Все обращения к PubChem проходят через backend.</p>
            </div>
          </section>
        </div>

        <ResultPanel isLoading={queryMutation.isPending} lastQuerySpec={lastQuerySpec} queryResult={queryResult} />
      </section>
    </main>
  );
}
