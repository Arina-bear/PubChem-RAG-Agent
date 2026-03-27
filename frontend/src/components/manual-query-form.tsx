"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import type { ManualQuerySpec } from "@/lib/types";

const manualQuerySchema = z.object({
  input_mode: z.enum(["name", "cid", "smiles"]),
  identifier: z.string().trim().min(1, "Введите значение для поиска."),
  operation: z.enum(["property", "record", "synonyms"]),
  include_raw: z.boolean(),
});

type ManualFormValues = z.infer<typeof manualQuerySchema>;

const identifierUiByMode: Record<ManualFormValues["input_mode"], { label: string; placeholder: string }> = {
  name: {
    label: "Введите название соединения",
    placeholder: "Например: aspirin",
  },
  cid: {
    label: "Введите CID",
    placeholder: "Например: 2244",
  },
  smiles: {
    label: "Введите строку SMILES",
    placeholder: "Например: CC(=O)OC1=CC=CC=C1C(=O)O",
  },
};

function toQuerySpec(values: ManualFormValues): ManualQuerySpec {
  return {
    domain: "compound",
    input_mode: values.input_mode,
    identifier: values.identifier,
    operation: values.operation,
    properties: [],
    filters: {},
    pagination: null,
    output: "json",
    include_raw: values.include_raw,
  };
}

export function ManualQueryForm({
  isLoading,
  onSubmit,
}: {
  isLoading: boolean;
  onSubmit: (spec: ManualQuerySpec) => void;
}) {
  const form = useForm<ManualFormValues>({
    resolver: zodResolver(manualQuerySchema),
    defaultValues: {
      input_mode: "name",
      identifier: "aspirin",
      operation: "property",
      include_raw: true,
    },
  });

  const watched = form.watch();
  const identifierUi = identifierUiByMode[watched.input_mode];
  const preview = useMemo(() => {
    const parsed = manualQuerySchema.safeParse(watched);
    if (!parsed.success) {
      return JSON.stringify(
        {
          domain: "compound",
          input_mode: watched.input_mode,
          identifier: watched.identifier,
          operation: watched.operation,
          properties: [],
          filters: {},
          pagination: null,
          output: "json",
          include_raw: watched.include_raw,
        },
        null,
        2,
      );
    }
    return JSON.stringify(toQuerySpec(parsed.data), null, 2);
  }, [watched]);

  return (
    <form
      className="glass-panel rounded-[28px] p-6 panel-strong"
      onSubmit={form.handleSubmit((values) => onSubmit(toQuerySpec(values)))}
    >
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.24em] text-[var(--muted)]">Ручной режим</p>
          <h2 className="mt-2 text-2xl font-semibold">Точный запрос к PubChem</h2>
          <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--muted)]">
            В интерфейсе доступны три самых понятных режима ввода: `name`, `cid` и `smiles`. Backend уже умеет больше, но
            в UI мы оставляем только самый надёжный и простой путь.
          </p>
        </div>
        <span className="rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-medium text-[var(--accent-strong)]">
          Домен зафиксирован: compound
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2">
          <span className="text-sm font-medium">Домен</span>
          <div className="rounded-2xl border border-[var(--border)] bg-white/80 px-4 py-3 text-sm">compound</div>
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium">Режим ввода</span>
          <select
            className="w-full rounded-2xl border border-[var(--border)] bg-white/80 px-4 py-3 text-sm outline-none"
            {...form.register("input_mode")}
          >
            <option value="name">Название</option>
            <option value="cid">CID</option>
            <option value="smiles">SMILES</option>
          </select>
        </label>

        <label className="space-y-2 md:col-span-2">
          <span className="text-sm font-medium">{identifierUi.label}</span>
          <input
            className="w-full rounded-2xl border border-[var(--border)] bg-white/80 px-4 py-3 text-sm outline-none"
            placeholder={identifierUi.placeholder}
            {...form.register("identifier")}
          />
          {form.formState.errors.identifier ? (
            <p className="text-sm text-[var(--warning)]">{form.formState.errors.identifier.message}</p>
          ) : null}
        </label>

        <label className="space-y-2">
          <span className="text-sm font-medium">Операция</span>
          <select
            className="w-full rounded-2xl border border-[var(--border)] bg-white/80 px-4 py-3 text-sm outline-none"
            {...form.register("operation")}
          >
            <option value="property">Свойства</option>
            <option value="record">Полная запись</option>
            <option value="synonyms">Синонимы</option>
          </select>
        </label>

        <label className="flex items-center gap-3 self-end rounded-2xl border border-[var(--border)] bg-white/80 px-4 py-3 text-sm">
          <input className="size-4 accent-[var(--accent)]" type="checkbox" {...form.register("include_raw")} />
          Добавить сырой ответ PubChem в итоговый JSON
        </label>
      </div>

      <details className="mt-5 rounded-2xl border border-[var(--border)] bg-white/70 p-4">
        <summary className="cursor-pointer text-sm font-medium">Дополнительные параметры и превью запроса</summary>
        <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
          Расширенные параметры, тяжёлые поиски и PUG View пока отложены. Ниже показан точный запрос, который будет
          отправлен прямо сейчас.
        </p>
        <pre className="mt-4 overflow-x-auto rounded-2xl bg-[#10231f] p-4 font-[family-name:var(--font-mono)] text-xs leading-6 text-[#d9fff8]">
          {preview}
        </pre>
      </details>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          className="rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-70"
          disabled={isLoading}
          type="submit"
        >
          {isLoading ? "Ищу..." : "Искать в PubChem"}
        </button>
        <p className="text-sm text-[var(--muted)]">
          В интерфейсе сейчас доступны режимы ввода `cid`, `name`, `smiles` и три безопасные операции: свойства,
          полная запись и синонимы.
        </p>
      </div>
    </form>
  );
}
