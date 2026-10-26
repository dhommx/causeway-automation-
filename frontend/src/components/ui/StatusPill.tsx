import clsx from "clsx";

const tones: Record<string, string> = {
  queued: "bg-muted text-muted-foreground",
  running: "bg-accent-soft text-primary",
  succeeded: "bg-success-soft text-success",
  failed: "bg-destructive-soft text-destructive",
  live: "bg-success-soft text-success",
  planned: "bg-muted text-muted-foreground",
};

const labels: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  live: "Live",
  planned: "Coming soon",
};

export default function StatusPill({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        tones[status] ?? "bg-muted text-muted-foreground",
      )}
    >
      {status === "running" && <span className="size-1.5 animate-pulse rounded-full bg-current" />}
      {labels[status] ?? status}
    </span>
  );
}
