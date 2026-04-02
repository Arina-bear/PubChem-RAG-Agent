"use client";

import { useEffect, useMemo, useState } from "react";

import { CompoundOverviewCard } from "@/components/compound-overview-card";
import { JsonPanel } from "@/components/json-panel";
import { ResultTabs } from "@/components/result-tabs";
import { buildAgentCurl } from "@/lib/api";
import type { AgentNormalizedPayload, AgentRequest, AgentResponseEnvelope, AgentToolCallTrace, CompoundOverview } from "@/lib/types";

type AgentTabId = "answer" | "compounds" | "analysis" | "tools" | "json";

export function AgentResultPanel({
  agentResult,
  isLoading,
  lastRequest,
}: {
  agentResult: AgentResponseEnvelope | null;
  isLoading: boolean;
  lastRequest: AgentRequest | null;
}) {
  const [activeTab, setActiveTab] = useState<AgentTabId>("answer");

  useEffect(() => {
    if (!agentResult) {
      return;
    }
    setActiveTab(agentResult.status === "needs_clarification" ? "analysis" : "answer");
  }, [agentResult]);

  const normalized = agentResult?.normalized ?? null;
  const compounds = useMemo(() => dedupeCompounds(normalized?.compounds ?? []), [normalized?.compounds]);
  const primaryCompound = compounds[0] ?? null;
  const alternativeCompounds = compounds.slice(1);
  const rawSteps = useMemo(() => extractRawSteps(agentResult?.raw ?? null), [agentResult?.raw]);
  const reasoningMoments = useMemo(() => buildReasoningMoments(normalized), [normalized]);
  const tabs = useMemo(
    () => [
      { id: "answer", label: "Ответ" },
      { id: "compounds", label: "Кандидаты" },
      { id: "analysis", label: "Ход агента" },
      { id: "tools", label: "Tools" },
      { id: "json", label: "JSON" },
    ] satisfies Array<{ id: AgentTabId; label: string }>,
    [],
  );

  const copyText = async (value: string) => {
    await navigator.clipboard.writeText(value);
  };

  return (
    <section className="glass-panel rounded-[32px] p-6 panel-strong">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--muted)]">Что вернул AI-агент</p>
          <h2 className="mt-2 text-2xl font-semibold">Ответ, кандидаты и trace инструментов</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Агентный ответ показывает не только финальный текст, но и то, как система поняла запрос, какие tools вызвала
            и на каких признаках основан результат.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-full border border-[var(--border)] px-4 py-2 text-xs font-medium"
            disabled={!agentResult}
            onClick={() => {
              if (agentResult) {
                void copyText(JSON.stringify(agentResult, null, 2));
              }
            }}
            type="button"
          >
            Скопировать JSON
          </button>
          <button
            className="rounded-full border border-[var(--border)] px-4 py-2 text-xs font-medium"
            disabled={!lastRequest}
            onClick={() => {
              if (lastRequest) {
                void copyText(buildAgentCurl(lastRequest));
              }
            }}
            type="button"
          >
            Скопировать cURL
          </button>
        </div>
      </div>

      {!agentResult ? (
        <div className="rounded-[30px] border border-dashed border-[var(--border)] bg-white/70 p-8">
          <p className="text-lg font-semibold">{isLoading ? "AI-агент анализирует запрос..." : "Агентный запрос ещё не запускался."}</p>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Напишите запрос естественным языком, чтобы увидеть parsed intent, tool trace, найденные соединения и итоговый
            ответ по PubChem.
          </p>
        </div>
      ) : agentResult.status === "error" ? (
        <div className="rounded-[30px] border border-[#e2b58c] bg-[#fff4eb] p-6">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--warning)]">Ошибка агента</p>
          <h3 className="mt-2 text-xl font-semibold">{agentResult.error?.code ?? "Неожиданная ошибка"}</h3>
          <p className="mt-3 text-sm leading-6 text-[#6d4522]">{agentResult.error?.message ?? "Не удалось выполнить агентный запрос."}</p>
          {agentResult.error?.details ? (
            <pre className="mt-4 overflow-x-auto rounded-2xl bg-white/70 p-4 text-xs leading-6 text-[#6d4522]">
              {JSON.stringify(agentResult.error.details, null, 2)}
            </pre>
          ) : null}
        </div>
      ) : (
        <div className="space-y-5">
          {agentResult.warnings.length ? (
            <div className="flex flex-wrap gap-2">
              {agentResult.warnings.map((warning) => (
                <span
                  className="rounded-full border border-[var(--border)] bg-[#fffaf1] px-3 py-1.5 text-xs font-medium text-[#7f5c12]"
                  key={`${warning.code}-${warning.message}`}
                >
                  {warning.message}
                </span>
              ))}
            </div>
          ) : null}

          {normalized ? <AgentSummaryStrip compounds={compounds} normalized={normalized} rawSteps={rawSteps.length} /> : null}

          <ResultTabs activeTab={activeTab} onChange={(tab) => setActiveTab(tab as AgentTabId)} tabs={tabs} />

          {activeTab === "answer" && normalized ? (
            <div className="space-y-4">
              <section className="rounded-[30px] border border-[var(--border)] bg-white/92 p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Финальный ответ</p>
                    <h3 className="mt-2 text-2xl font-semibold">
                      {agentResult.status === "needs_clarification" ? "Агент просит уточнение" : "Агент нашёл рабочий ответ"}
                    </h3>
                  </div>
                  <span className="rounded-full border border-[var(--border)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--muted)]">
                    {normalized.provider} · {normalized.model}
                  </span>
                </div>
                <div className="mt-4 rounded-3xl bg-[#f8f6f1] p-5 text-sm leading-7 whitespace-pre-wrap">
                  {normalized.answer}
                </div>
              </section>

              {normalized.needs_clarification && normalized.clarification_question ? (
                <section className="rounded-[30px] border border-[#e4c28f] bg-[#fff8ef] p-6">
                  <p className="text-xs font-medium uppercase tracking-[0.18em] text-[#9a6c21]">Следующий шаг</p>
                  <p className="mt-3 text-base leading-7 text-[#6d4a16]">{normalized.clarification_question}</p>
                </section>
              ) : null}

              <section className="rounded-[30px] border border-[var(--border)] bg-white/92 p-6">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Почему агент пришёл к этому результату</p>
                <div className="mt-4 space-y-3">
                  {reasoningMoments.map((moment) => (
                    <div className="rounded-2xl border border-[var(--border)] bg-[#fcfcf7] px-4 py-3 text-sm leading-6" key={moment}>
                      {moment}
                    </div>
                  ))}
                </div>
              </section>
            </div>
          ) : null}

          {activeTab === "compounds" ? (
            compounds.length ? (
              <div className="space-y-4">
                <CompoundOverviewCard compound={primaryCompound} />

                {alternativeCompounds.length ? (
                  <section className="rounded-[30px] border border-[var(--border)] bg-white/92 p-6">
                    <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Другие кандидаты</p>
                    <div className="mt-4 grid gap-4 xl:grid-cols-2">
                      {alternativeCompounds.map((compound) => (
                        <CompactCompoundCard compound={compound} key={compound.cid} />
                      ))}
                    </div>
                  </section>
                ) : null}
              </div>
            ) : (
              <EmptySubpanel
                description={
                  normalized?.needs_clarification
                    ? "Агент остановился до PubChem-поиска и попросил уточнить формулу, название, SMILES или диапазон массы."
                    : "В tool trace пока нет извлечённых compounds. Это повод проверить стратегию поиска и raw JSON."
                }
                title="Кандидаты пока не появились"
              />
            )
          ) : null}

          {activeTab === "analysis" && normalized ? (
            <div className="space-y-4">
              <section className="rounded-[30px] border border-[var(--border)] bg-white/92 p-6">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Что агент понял из текста</p>
                <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {buildParsedSignalCards(normalized).map((item) => (
                    <SignalCard key={item.label} label={item.label} value={item.value} />
                  ))}
                </div>
              </section>

              <section className="rounded-[30px] border border-[var(--border)] bg-white/92 p-6">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Ход агента</p>
                <div className="mt-4 space-y-3">
                  {reasoningMoments.map((moment, index) => (
                    <div className="flex gap-3" key={`${index + 1}-${moment}`}>
                      <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[var(--accent)] text-xs font-semibold text-white">
                        {index + 1}
                      </div>
                      <div className="flex-1 rounded-2xl border border-[var(--border)] bg-[#fcfcf7] px-4 py-3 text-sm leading-6">
                        {moment}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          ) : null}

          {activeTab === "tools" && normalized ? (
            normalized.tool_calls.length ? (
              <div className="space-y-4">
                {normalized.tool_calls.map((toolCall, index) => (
                  <ToolTraceCard key={toolCall.id || `${toolCall.name}-${index}`} step={index + 1} toolCall={toolCall} />
                ))}
              </div>
            ) : (
              <EmptySubpanel
                description="Агент пока не вызвал ни одного tool. Обычно это значит, что он попросил уточнение ещё до PubChem-поиска."
                title="Tool trace пуст"
              />
            )
          ) : null}

          {activeTab === "json" ? (
            <JsonPanel
              normalized={agentResult.normalized}
              onCopyNormalized={() => void copyText(JSON.stringify(agentResult.normalized, null, 2))}
              onCopyRaw={() => void copyText(JSON.stringify(agentResult.raw, null, 2))}
              raw={agentResult.raw}
            />
          ) : null}
        </div>
      )}
    </section>
  );
}

function AgentSummaryStrip({
  normalized,
  compounds,
  rawSteps,
}: {
  normalized: AgentNormalizedPayload;
  compounds: CompoundOverview[];
  rawSteps: number;
}) {
  const cards = [
    {
      label: "Статус",
      value: normalized.needs_clarification ? "Нужно уточнение" : "Ответ готов",
    },
    {
      label: "Режим поиска",
      value: normalized.parsed_query.recommended_search_mode,
    },
    {
      label: "Уверенность parse",
      value: `${Math.round(normalized.parsed_query.confidence * 100)}%`,
    },
    {
      label: "Вызвано tools",
      value: String(normalized.tool_calls.length),
    },
    {
      label: "Найдено compounds",
      value: String(compounds.length),
    },
    {
      label: "LLM steps",
      value: String(rawSteps),
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {cards.map((card) => (
        <div className="rounded-3xl border border-[var(--border)] bg-white/90 p-4" key={card.label}>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">{card.label}</p>
          <p className="mt-3 text-lg font-semibold">{card.value}</p>
        </div>
      ))}
    </div>
  );
}

function ToolTraceCard({ step, toolCall }: { step: number; toolCall: AgentToolCallTrace }) {
  return (
    <section className="rounded-[30px] border border-[var(--border)] bg-white/92 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Шаг {step}</p>
          <h3 className="mt-2 text-xl font-semibold">{friendlyToolName(toolCall.name)}</h3>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{toolExplanation(toolCall.name)}</p>
        </div>
        <span
          className={`rounded-full px-3 py-1.5 text-xs font-medium ${
            toolCall.status === "success"
              ? "border border-[#bfe0d4] bg-[#eefaf5] text-[#1a6d59]"
              : "border border-[#efc5b3] bg-[#fff3ee] text-[#9e4a2d]"
          }`}
        >
          {toolCall.status === "success" ? "Успешно" : "Ошибка"}
        </span>
      </div>

      {toolCall.error_message ? (
        <div className="mt-4 rounded-2xl border border-[#efc5b3] bg-[#fff5f1] px-4 py-3 text-sm leading-6 text-[#8c4227]">
          {toolCall.error_message}
        </div>
      ) : null}

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <TracePayloadCard title="Аргументы" payload={toolCall.arguments} />
        <TracePayloadCard title="Результат" payload={toolCall.result} />
      </div>
    </section>
  );
}

function TracePayloadCard({ title, payload }: { title: string; payload: unknown }) {
  return (
    <div className="rounded-3xl border border-[var(--border)] bg-[#fcfcf7] p-4">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">{title}</p>
      <pre className="mt-3 overflow-x-auto rounded-2xl bg-white/90 p-4 text-xs leading-6 text-[#29353c]">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </div>
  );
}

function CompactCompoundCard({ compound }: { compound: CompoundOverview }) {
  return (
    <div className="rounded-[28px] border border-[var(--border)] bg-[#fcfcf7] p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Кандидат</p>
          <h3 className="mt-2 text-xl font-semibold">{compound.title ?? `Соединение ${compound.cid}`}</h3>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{compound.iupac_name ?? "Название IUPAC недоступно."}</p>
        </div>
        <span className="rounded-full border border-[var(--border)] bg-white px-3 py-1.5 text-xs font-medium">CID {compound.cid}</span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <SignalCard label="Формула" value={compound.molecular_formula ?? "Нет данных"} />
        <SignalCard label="Молекулярная масса" value={formatNumber(compound.molecular_weight)} />
        <SignalCard label="SMILES" value={compound.canonical_smiles ?? "Нет данных"} />
        <SignalCard label="InChIKey" value={compound.inchi_key ?? "Нет данных"} />
      </div>
    </div>
  );
}

function SignalCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-3xl border border-[var(--border)] bg-[#fcfcf7] p-4">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">{label}</p>
      <p className="mt-3 text-sm leading-6 break-words">{value}</p>
    </div>
  );
}

function EmptySubpanel({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-[30px] border border-dashed border-[var(--border)] bg-white/70 p-8">
      <p className="text-lg font-semibold">{title}</p>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted)]">{description}</p>
    </div>
  );
}

function dedupeCompounds(compounds: CompoundOverview[]): CompoundOverview[] {
  const unique = new Map<number, CompoundOverview>();
  for (const compound of compounds) {
    if (!unique.has(compound.cid)) {
      unique.set(compound.cid, compound);
    }
  }
  return Array.from(unique.values());
}

function extractRawSteps(raw: AgentResponseEnvelope["raw"]): unknown[] {
  if (!raw || typeof raw !== "object" || !("steps" in raw)) {
    return [];
  }
  const steps = raw.steps;
  return Array.isArray(steps) ? steps : [];
}

function buildParsedSignalCards(normalized: AgentNormalizedPayload): Array<{ label: string; value: string }> {
  const parsed = normalized.parsed_query;

  return [
    { label: "Язык запроса", value: parsed.language },
    { label: "Рекомендуемый режим", value: parsed.recommended_search_mode },
    { label: "Название соединения", value: parsed.compound_name ?? "Не извлечено" },
    { label: "SMILES", value: parsed.smiles ?? "Не извлечено" },
    { label: "Формула", value: parsed.formula ?? "Не извлечено" },
    { label: "Диапазон массы", value: formatMassRange(parsed.mass_range) },
    { label: "Смысловые признаки", value: parsed.synonyms.length ? parsed.synonyms.join(", ") : "Не извлечены" },
    { label: "Неясности", value: parsed.ambiguities.length ? parsed.ambiguities.join(" | ") : "Не обнаружены" },
  ];
}

function buildReasoningMoments(normalized: AgentNormalizedPayload | null): string[] {
  if (!normalized) {
    return [];
  }

  const parsed = normalized.parsed_query;
  const moments: string[] = [];

  if (parsed.compound_name) {
    moments.push(`Из текста извлечено название соединения: ${parsed.compound_name}.`);
  }
  if (parsed.smiles) {
    moments.push(`Агент распознал точную структуру по SMILES: ${parsed.smiles}.`);
  }
  if (parsed.formula) {
    moments.push(`Агент извлёк молекулярную формулу: ${parsed.formula}.`);
  }
  if (parsed.mass_range) {
    moments.push(`Агент выделил массовое ограничение ${formatMassRange(parsed.mass_range)}.`);
  }
  if (parsed.synonyms.length) {
    moments.push(`Дополнительно замечены смысловые признаки: ${parsed.synonyms.join(", ")}.`);
  }

  if (!normalized.tool_calls.length) {
    if (normalized.needs_clarification) {
      moments.push("На этом этапе агент не пошёл в PubChem и вместо этого запросил уточнение, чтобы снизить риск ложного совпадения.");
    } else {
      moments.push("Агент завершил ответ без tool trace, поэтому стоит проверить raw JSON и prompt.");
    }
    return moments;
  }

  normalized.tool_calls.forEach((toolCall, index) => {
    moments.push(`Шаг ${index + 1}: агент вызвал ${friendlyToolName(toolCall.name)} и получил статус "${toolCall.status}".`);
  });

  if (normalized.compounds.length) {
    const compound = normalized.compounds[0];
    moments.push(
      `Финальный ответ опирается на candidate CID ${compound.cid}${compound.title ? ` (${compound.title})` : ""} и данные, возвращённые tools.`,
    );
  } else if (normalized.needs_clarification) {
    moments.push("Даже после разбора запроса агент не получил достаточно надёжного кандидата и оставил вопрос пользователю.");
  }

  return moments;
}

function friendlyToolName(toolName: string): string {
  const names: Record<string, string> = {
    search_compound_by_name: "search_compound_by_name",
    search_compound_by_smiles: "search_compound_by_smiles",
    search_compound_by_formula: "search_compound_by_formula",
    search_compound_by_mass_range: "search_compound_by_mass_range",
    get_compound_summary: "get_compound_summary",
    name_to_smiles: "name_to_smiles",
    search_by_synonym: "search_by_synonym",
    ask_user_for_clarification: "ask_user_for_clarification",
  };
  return names[toolName] ?? toolName;
}

function toolExplanation(toolName: string): string {
  const explanations: Record<string, string> = {
    search_compound_by_name: "Поиск соединения по явному названию или короткому ключевому слову.",
    search_compound_by_smiles: "Поиск соединения по точной структурной записи SMILES.",
    search_compound_by_formula: "Поиск по молекулярной формуле, если она извлечена из текста.",
    search_compound_by_mass_range: "Поиск кандидатов по диапазону молекулярной массы.",
    get_compound_summary: "Дозапрос сводки свойств по найденному CID.",
    name_to_smiles: "Промежуточное преобразование названия вещества в канонический SMILES.",
    search_by_synonym: "Поиск соединения по альтернативному названию или синониму.",
    ask_user_for_clarification: "Безопасная остановка агента с уточняющим вопросом.",
  };
  return explanations[toolName] ?? "Внутренний tool агента.";
}

function formatMassRange(value: [number, number] | null | undefined): string {
  if (!value) {
    return "Не извлечён";
  }
  return `${formatNumber(value[0])} – ${formatNumber(value[1])}`;
}

function formatNumber(value: number | null | undefined): string {
  if (value == null) {
    return "Нет данных";
  }
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 6 }).format(value);
}
