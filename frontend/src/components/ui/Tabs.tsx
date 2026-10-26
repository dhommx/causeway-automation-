import clsx from "clsx";
import type { ReactNode } from "react";

type Tab<T extends string> = { value: T; label: string; icon?: ReactNode };

export default function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  size = "md",
}: {
  tabs: Tab<T>[];
  value: T;
  onChange: (v: T) => void;
  size?: "md" | "sm";
}) {
  return (
    <div role="tablist" className="inline-flex rounded-[var(--radius)] bg-muted p-1">
      {tabs.map((t) => (
        <button
          key={t.value}
          role="tab"
          type="button"
          aria-selected={value === t.value}
          onClick={() => onChange(t.value)}
          className={clsx(
            "inline-flex cursor-pointer items-center gap-2 rounded-[calc(var(--radius)-2px)] font-medium transition-colors duration-150",
            size === "md" ? "min-h-9 px-4 text-sm" : "min-h-7 px-3 text-xs",
            value === t.value ? "bg-card text-primary shadow-sm" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {t.icon}
          {t.label}
        </button>
      ))}
    </div>
  );
}
