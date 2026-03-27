"use client";

export function SynonymsPanel({ synonyms }: { synonyms: string[] }) {
  if (!synonyms.length) {
    return (
      <div className="rounded-3xl border border-dashed border-[var(--border)] bg-white/70 p-8 text-sm leading-6 text-[var(--muted)]">
        Для этого соединения PubChem не вернул синонимы.
      </div>
    );
  }

  return (
    <div className="rounded-[30px] border border-[var(--border)] bg-white/92 p-6">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Синонимы</p>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {synonyms.map((synonym) => (
          <div className="rounded-2xl border border-[var(--border)] bg-[#fcfcf7] px-4 py-3 text-sm" key={synonym}>
            {synonym}
          </div>
        ))}
      </div>
    </div>
  );
}
