"use client";

import type { CompoundOverview } from "@/lib/types";

export function CompoundOverviewCard({ compound }: { compound: CompoundOverview | null }) {
  if (!compound) {
    return (
      <div className="rounded-3xl border border-dashed border-[var(--border)] bg-white/70 p-8 text-sm leading-6 text-[var(--muted)]">
        Выполните запрос, чтобы здесь появилась карточка соединения.
      </div>
    );
  }

  return (
    <div className="rounded-[30px] border border-[var(--border)] bg-white/92 p-6">
      <div className="grid gap-6 lg:grid-cols-[180px_1fr]">
        <div className="overflow-hidden rounded-[26px] border border-[var(--border)] bg-[linear-gradient(180deg,#f0fbf7_0%,#e7eff2_100%)] p-5">
          {compound.image_data_url ? (
            <img
              alt={compound.title ?? `Соединение ${compound.cid}`}
              className="mx-auto h-[140px] w-[140px] object-contain"
              src={compound.image_data_url}
            />
          ) : (
            <div className="flex h-[140px] items-center justify-center text-sm text-[var(--muted)]">Нет изображения</div>
          )}
        </div>

        <div>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Обзор</p>
              <h3 className="mt-2 text-3xl font-semibold">{compound.title ?? `Соединение ${compound.cid}`}</h3>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">{compound.iupac_name ?? "Название IUPAC недоступно."}</p>
            </div>
            <div className="rounded-full bg-[var(--accent-soft)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)]">
              CID {compound.cid}
            </div>
          </div>

          <div className="data-grid mt-6">
            <Metric label="Формула" value={compound.molecular_formula} />
            <Metric label="Молекулярная масса" value={formatNumber(compound.molecular_weight)} />
            <Metric label="Точная масса" value={formatNumber(compound.exact_mass)} />
            <Metric label="XLogP" value={formatNumber(compound.xlogp)} />
            <Metric label="TPSA" value={formatNumber(compound.tpsa)} />
            <Metric label="InChIKey" value={compound.inchi_key} mono />
            <Metric label="Канонический SMILES" value={compound.canonical_smiles} mono spanFull />
          </div>

          {compound.synonyms_preview.length ? (
            <div className="mt-6">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Короткий список синонимов</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {compound.synonyms_preview.map((synonym) => (
                  <span
                    className="rounded-full border border-[var(--border)] bg-white px-3 py-1.5 text-xs font-medium"
                    key={synonym}
                  >
                    {synonym}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  mono = false,
  spanFull = false,
}: {
  label: string;
  value: string | number | null | undefined;
  mono?: boolean;
  spanFull?: boolean;
}) {
  return (
    <div className={`rounded-3xl border border-[var(--border)] bg-[#fcfcf7] p-4 ${spanFull ? "md:col-span-2" : ""}`}>
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">{label}</p>
      <p className={`mt-3 text-sm leading-6 ${mono ? "font-[family-name:var(--font-mono)]" : ""}`}>{value ?? "Нет данных"}</p>
    </div>
  );
}

function formatNumber(value: number | null | undefined): string | null {
  if (value == null) {
    return null;
  }
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 6 }).format(value);
}
