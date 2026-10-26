import clsx from "clsx";

const tones: Record<string, string> = {
  neutral: "text-foreground",
  good: "text-success",
  warn: "text-warning",
  bad: "text-destructive",
};

export default function MetricTile({ label, value, tone = "neutral" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-border bg-card px-5 py-4">
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
      <p className={clsx("mt-1 text-3xl font-semibold tabular-nums", tones[tone])}>{value}</p>
    </div>
  );
}
