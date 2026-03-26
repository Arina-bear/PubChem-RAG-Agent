"use client";

export function JsonPanel({
  normalized,
  raw,
  onCopyNormalized,
  onCopyRaw,
}: {
  normalized: unknown;
  raw: unknown;
  onCopyNormalized: () => void;
  onCopyRaw: () => void;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <section className="rounded-[30px] border border-[var(--border)] bg-[#10231f] p-5 text-[#d9fff8]">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-[#92c9c0]">Нормализованный ответ</p>
            <p className="mt-1 text-sm text-[#bfe8e2]">Это стабильный контракт, на который опирается UI.</p>
          </div>
          <button
            className="rounded-full border border-[#2d655d] px-3 py-2 text-xs font-medium text-[#d9fff8]"
            onClick={onCopyNormalized}
            type="button"
          >
            Скопировать JSON
          </button>
        </div>
        <pre className="overflow-x-auto text-xs leading-6">{JSON.stringify(normalized, null, 2)}</pre>
      </section>

      <section className="rounded-[30px] border border-[var(--border)] bg-white/92 p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">Сырой ответ</p>
            <p className="mt-1 text-sm text-[var(--muted)]">Исходный ответ upstream-сервиса без влияния на отрисовку интерфейса.</p>
          </div>
          <button
            className="rounded-full border border-[var(--border)] px-3 py-2 text-xs font-medium"
            onClick={onCopyRaw}
            type="button"
          >
            Скопировать raw
          </button>
        </div>
        <pre className="overflow-x-auto rounded-3xl bg-[#f5f4ef] p-4 text-xs leading-6 text-[#29353c]">
          {JSON.stringify(raw, null, 2)}
        </pre>
      </section>
    </div>
  );
}
