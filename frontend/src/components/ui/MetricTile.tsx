import clsx from "clsx";

const tones: Record<string, string> = {
  neutral: "text-foreground",
  good: "text-success",
  warn: "text-warning",
  bad: "text-destructive",
};

export default function MetricTile({ label, value, tone = "neutral" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-[var(--radius)] border border-border bg-card px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={clsx("mt-0.5 text-xl font-semibold tabular-nums", tones[tone])}>{value}</p>
    </div>
  );
}
