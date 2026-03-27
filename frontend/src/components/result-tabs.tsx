"use client";

export function ResultTabs({
  activeTab,
  onChange,
  tabs,
}: {
  activeTab: string;
  onChange: (tab: string) => void;
  tabs: Array<{ id: string; label: string }>;
}) {
  return (
    <div className="inline-flex rounded-full border border-[var(--border)] bg-white/90 p-1">
      {tabs.map((tab) => {
        const selected = activeTab === tab.id;
        return (
          <button
            className={`rounded-full px-4 py-2 text-sm font-medium transition ${
              selected ? "bg-[var(--accent)] text-white" : "text-[var(--muted)] hover:text-[var(--foreground)]"
            }`}
            key={tab.id}
            onClick={() => onChange(tab.id)}
            type="button"
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
