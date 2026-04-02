"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import type { AgentRequest, LLMProviderName } from "@/lib/types";

const EXAMPLE_PROMPTS = [
  "антибиотик с бензольным кольцом, молекулярная масса около 350",
  "соединение похоже на aspirin",
  "найди молекулу по описанию и верни свойства",
  "acetone",
] as const;

const agentRequestSchema = z.object({
  text: z.string().trim().min(1, "Опишите, что вы хотите найти."),
  provider: z.enum(["modal_glm", "openai"]),
  include_raw: z.boolean(),
});

type AgentFormValues = z.infer<typeof agentRequestSchema>;

function toAgentRequest(values: AgentFormValues): AgentRequest {
  return {
    text: values.text,
    provider: values.provider,
    include_raw: values.include_raw,
    max_steps: 6,
    max_output_tokens: 900,
  };
}

function providerLabel(provider: LLMProviderName): string {
  if (provider === "modal_glm") {
    return "Modal GLM-5";
  }
  return "OpenAI";
}

export function AgentQueryForm({
  isLoading,
  onSubmit,
}: {
  isLoading: boolean;
  onSubmit: (request: AgentRequest) => void;
}) {
  const form = useForm<AgentFormValues>({
    resolver: zodResolver(agentRequestSchema),
    defaultValues: {
      text: EXAMPLE_PROMPTS[0],
      provider: "modal_glm",
      include_raw: true,
    },
  });

  return (
    <form
      className="glass-panel rounded-[28px] p-6 panel-strong"
      onSubmit={form.handleSubmit((values) => onSubmit(toAgentRequest(values)))}
    >
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--muted)]">AI-агент</p>
          <h2 className="mt-2 text-2xl font-semibold">Natural-language поиск через tools</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Напишите запрос обычным языком. Агент сначала выделит полезные признаки, затем сам выберет подходящие
            PubChem tools и вернёт ответ с объяснением, кандидатами и trace шагов.
          </p>
        </div>
        <span className="rounded-full border border-[var(--border)] bg-white/90 px-4 py-2 text-xs font-medium text-[var(--muted)]">
          V1: parsed intent → tool calling → compounds → explanation
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
        <label className="space-y-2 md:row-span-2">
          <span className="text-sm font-medium">Опишите, что нужно найти</span>
          <textarea
            className="min-h-[200px] w-full rounded-3xl border border-[var(--border)] bg-white/80 px-4 py-4 text-sm leading-6 outline-none"
            placeholder="Например: антибиотик с бензольным кольцом, молекулярная масса около 350"
            {...form.register("text")}
          />
          {form.formState.errors.text ? <p className="text-sm text-[var(--warning)]">{form.formState.errors.text.message}</p> : null}
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium">LLM provider</span>
          <select
            className="w-full rounded-2xl border border-[var(--border)] bg-white/80 px-4 py-3 text-sm outline-none"
            {...form.register("provider")}
          >
            {(["modal_glm", "openai"] as const).map((provider) => (
              <option key={provider} value={provider}>
                {providerLabel(provider)}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-3 rounded-2xl border border-[var(--border)] bg-white/80 px-4 py-3 text-sm">
          <input className="size-4 accent-[var(--accent)]" type="checkbox" {...form.register("include_raw")} />
          Сохранять raw steps для JSON и agent trace
        </label>
      </div>

      <div className="mt-5">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Быстрые примеры</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLE_PROMPTS.map((example) => (
            <button
              className="rounded-full border border-[var(--border)] bg-white/85 px-4 py-2 text-left text-xs font-medium text-[var(--ink-soft)] transition hover:border-[var(--accent)]/45 hover:text-[var(--ink)]"
              key={example}
              onClick={() => form.setValue("text", example, { shouldDirty: true, shouldValidate: true })}
              type="button"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-3">
        <div className="rounded-3xl border border-[var(--border)] bg-white/90 p-4">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">1. Понимание запроса</p>
          <p className="mt-3 text-sm leading-6 text-[var(--muted)]">Агент выделяет название, формулу, SMILES, массу и смысловые признаки.</p>
        </div>
        <div className="rounded-3xl border border-[var(--border)] bg-white/90 p-4">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">2. Tool calling</p>
          <p className="mt-3 text-sm leading-6 text-[var(--muted)]">LLM сама выбирает нужные PubChem tools вместо жёстко прошитого сценария.</p>
        </div>
        <div className="rounded-3xl border border-[var(--border)] bg-white/90 p-4">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">3. Ответ с объяснением</p>
          <p className="mt-3 text-sm leading-6 text-[var(--muted)]">Интерфейс покажет ответ, кандидатов, parsed intent, trace шагов и JSON для отладки.</p>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          className="rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-70"
          disabled={isLoading}
          type="submit"
        >
          {isLoading ? "Агент работает..." : "Запустить AI-агента"}
        </button>
        <p className="text-sm text-[var(--muted)]">
          Для сложных и неоднозначных описаний агент может вернуть уточняющий вопрос вместо молчаливой галлюцинации.
        </p>
      </div>
    </form>
  );
}
