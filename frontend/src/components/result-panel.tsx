"use client";

import { useEffect, useMemo, useState } from "react";

import { CompoundOverviewCard } from "@/components/compound-overview-card";
import { JsonPanel } from "@/components/json-panel";
import { ResultTabs } from "@/components/result-tabs";
import { SynonymsPanel } from "@/components/synonyms-panel";
import { buildQueryCurl } from "@/lib/api";
import type { ManualQuerySpec, QueryResponseEnvelope } from "@/lib/types";

export function ResultPanel({
  isLoading,
  queryResult,
  lastQuerySpec,
}: {
  isLoading: boolean;
  queryResult: QueryResponseEnvelope | null;
  lastQuerySpec: ManualQuerySpec | null;
}) {
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    if (queryResult?.presentation_hints?.active_tab) {
      setActiveTab(queryResult.presentation_hints.active_tab);
    }
  }, [queryResult]);

  const tabs = useMemo(
    () => [
      { id: "overview", label: "Обзор" },
      { id: "synonyms", label: "Синонимы" },
      { id: "json", label: "JSON" },
    ],
    [],
  );

  const copyText = async (value: string) => {
    await navigator.clipboard.writeText(value);
  };

  return (
    <section className="glass-panel rounded-[32px] p-6 panel-strong">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--muted)]">Что вернул PubChem</p>
          <h2 className="mt-2 text-2xl font-semibold">Результаты по соединению</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Сначала интерфейс показывает нормализованный ответ. Сырой ответ PubChem остаётся доступен во вкладке `JSON`.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-full border border-[var(--border)] px-4 py-2 text-xs font-medium"
            disabled={!queryResult}
            onClick={() => {
              if (queryResult) {
                void copyText(JSON.stringify(queryResult, null, 2));
              }
            }}
            type="button"
          >
            Скопировать JSON
          </button>
          <button
            className="rounded-full border border-[var(--border)] px-4 py-2 text-xs font-medium"
            disabled={!lastQuerySpec}
            onClick={() => {
              if (lastQuerySpec) {
                void copyText(buildQueryCurl(lastQuerySpec));
              }
            }}
            type="button"
          >
            Скопировать cURL
          </button>
        </div>
      </div>

      {!queryResult ? (
        <div className="rounded-[30px] border border-dashed border-[var(--border)] bg-white/70 p-8">
          <p className="text-lg font-semibold">{isLoading ? "Получаю данные из PubChem..." : "Запрос ещё не запускался."}</p>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Выполните ручной поиск или сначала разберите текстовый запрос через агентный режим, чтобы увидеть обзор, синонимы и
            сырой JSON от PubChem.
          </p>
        </div>
      ) : queryResult.status === "error" ? (
        <div className="rounded-[30px] border border-[#e2b58c] bg-[#fff4eb] p-6">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--warning)]">Ошибка</p>
          <h3 className="mt-2 text-xl font-semibold">{queryResult.error?.code ?? "Неожиданная ошибка"}</h3>
          <p className="mt-3 text-sm leading-6 text-[#6d4522]">{queryResult.error?.message ?? "Не удалось выполнить запрос."}</p>
          {queryResult.error?.details ? (
            <pre className="mt-4 overflow-x-auto rounded-2xl bg-white/70 p-4 text-xs leading-6 text-[#6d4522]">
              {JSON.stringify(queryResult.error.details, null, 2)}
            </pre>
          ) : null}
        </div>
      ) : (
        <div className="space-y-5">
          {queryResult.warnings.length ? (
            <div className="flex flex-wrap gap-2">
              {queryResult.warnings.map((warning) => (
                <span
                  className="rounded-full border border-[var(--border)] bg-[#fffaf1] px-3 py-1.5 text-xs font-medium text-[#7f5c12]"
                  key={`${warning.code}-${warning.message}`}
                >
                  {warning.message}
                </span>
              ))}
            </div>
          ) : null}

          <ResultTabs activeTab={activeTab} onChange={setActiveTab} tabs={tabs} />

          {activeTab === "overview" ? (
            <CompoundOverviewCard compound={queryResult.normalized?.primary_result ?? null} />
          ) : null}
          {activeTab === "synonyms" ? <SynonymsPanel synonyms={queryResult.normalized?.synonyms ?? []} /> : null}
          {activeTab === "json" ? (
            <JsonPanel
              normalized={queryResult.normalized}
              onCopyNormalized={() => void copyText(JSON.stringify(queryResult.normalized, null, 2))}
              onCopyRaw={() => void copyText(JSON.stringify(queryResult.raw, null, 2))}
              raw={queryResult.raw}
            />
          ) : null}
        </div>
      )}
    </section>
  );
}
