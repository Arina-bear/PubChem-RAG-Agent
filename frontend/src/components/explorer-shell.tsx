"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { AgentResultPanel } from "@/components/agent-result-panel";
import { AgentQueryForm } from "@/components/agent-query-form";
import { ManualQueryForm } from "@/components/manual-query-form";
import { ResultPanel } from "@/components/result-panel";
import { runAgent, runQuery } from "@/lib/api";
import type { AgentRequest, AgentResponseEnvelope, ManualQuerySpec, QueryResponseEnvelope } from "@/lib/types";

type ExplorerMode = "manual" | "agent";

export function ExplorerShell() {
  const [mode, setMode] = useState<ExplorerMode>("agent");
  const [queryResult, setQueryResult] = useState<QueryResponseEnvelope | null>(null);
  const [lastQuerySpec, setLastQuerySpec] = useState<ManualQuerySpec | null>(null);
  const [agentResult, setAgentResult] = useState<AgentResponseEnvelope | null>(null);
  const [lastAgentRequest, setLastAgentRequest] = useState<AgentRequest | null>(null);

  const queryMutation = useMutation({
    mutationFn: runQuery,
    onMutate: () => {
      setQueryResult(null);
    },
    onSuccess: (response) => {
      setQueryResult(response.data);
    },
  });

  const agentMutation = useMutation({
    mutationFn: runAgent,
    onMutate: () => {
      setAgentResult(null);
    },
    onSuccess: (response) => {
      setAgentResult(response.data);
    },
  });

  const handleManualSubmit = (spec: ManualQuerySpec) => {
    setLastQuerySpec(spec);
    queryMutation.mutate(spec);
  };

  const handleAgentSubmit = (request: AgentRequest) => {
    setLastAgentRequest(request);
    agentMutation.mutate(request);
  };

  return (
    <main className="mx-auto max-w-[1500px] px-4 py-8 md:px-6 lg:px-8">
      <section className="mb-8 rounded-[36px] border border-[var(--border)] bg-white/70 p-6 shadow-[var(--shadow)] backdrop-blur md:p-8">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.26em] text-[var(--muted)]">PubChem Compound Explorer</p>
            <h1 className="mt-3 max-w-4xl text-4xl font-semibold leading-tight md:text-5xl">
              Natural-language поиск соединений в PubChem через AI-агента и точные tools
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-[var(--muted)] md:text-base">
              Теперь агентный режим принимает естественный язык, сам извлекает признаки, выбирает PubChem tools и
              возвращает объяснимый результат: ответ, кандидаты, trace вызванных инструментов и машинный разбор запроса.
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
            <AgentQueryForm isLoading={agentMutation.isPending} onSubmit={handleAgentSubmit} />
          )}

          <section className="glass-panel rounded-[28px] p-6">
            <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--muted)]">Как это работает</p>
            <div className="mt-4 space-y-3 text-sm leading-6 text-[var(--muted)]">
              {mode === "agent" ? (
                <>
                  <p>Пользователь пишет на естественном языке, а агент сначала выделяет химические признаки из текста.</p>
                  <p>Дальше LLM сама выбирает нужные tools для PubChem и строит ответ с объяснением пути поиска.</p>
                  <p>Во фронтенде доступны parsed intent, tool trace, найденные соединения и сырой JSON для отладки.</p>
                </>
              ) : (
                <>
                  <p>Ручной режим отправляет типизированный запрос прямо в backend без LLM-агента.</p>
                  <p>Этот путь полезен для точного поиска по `name`, `cid` или `smiles` и для проверки API-контракта.</p>
                  <p>Все обращения к PubChem и любым LLM проходят через backend, браузер не ходит наружу напрямую.</p>
                </>
              )}
            </div>
          </section>
        </div>

        {mode === "manual" ? (
          <ResultPanel isLoading={queryMutation.isPending} lastQuerySpec={lastQuerySpec} queryResult={queryResult} />
        ) : (
          <AgentResultPanel
            agentResult={agentResult}
            isLoading={agentMutation.isPending}
            lastRequest={lastAgentRequest}
          />
        )}
      </section>
    </main>
  );
}
