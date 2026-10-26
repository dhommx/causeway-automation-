import clsx from "clsx";
import { History } from "lucide-react";
import { useEffect, useState } from "react";

import type { Workflow } from "../../lib/api";
import { duration, formatDateTime, useRuns } from "../../lib/runs";
import EmptyState from "../ui/EmptyState";
import Panel from "../ui/Panel";
import StatusPill from "../ui/StatusPill";
import RunDetail from "./RunDetail";

export default function HistoryTab({ wf }: { wf: Workflow }) {
  const { data: runs, isLoading } = useRuns(wf.key);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (!selected && runs?.length) setSelected(runs[0].id);
  }, [runs, selected]);

  const run = runs?.find((r) => r.id === selected) ?? null;

  return (
    <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[minmax(340px,440px)_1fr]">
      <Panel title={`Runs${runs ? ` (${runs.length})` : ""}`}>
        {isLoading && <div className="m-5 h-40 animate-pulse rounded-[var(--radius)] bg-muted" />}
        {runs?.length === 0 && (
          <EmptyState icon={<History className="size-5" />} title="No runs yet">
            Every run of this automation will be listed here with its files, rules and result.
          </EmptyState>
        )}
        <ul className="divide-y divide-border">
          {runs?.map((r) => {
            const inputs = r.files.filter((f) => f.role === "input");
            return (
              <li key={r.id}>
                <button
                  type="button"
                  onClick={() => setSelected(r.id)}
                  aria-current={r.id === selected}
                  className={clsx(
                    "grid w-full cursor-pointer gap-1 border-s-[3px] px-5 py-3 text-start transition-colors duration-150",
                    r.id === selected ? "border-accent bg-accent-soft/60" : "border-transparent hover:bg-muted",
                  )}
                >
                  <span className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium tabular-nums">{formatDateTime(r.created_at)}</span>
                    <StatusPill status={r.status} />
                  </span>
                  <span className="truncate text-xs text-muted-foreground">
                    {inputs.map((f) => f.file.original_name).join(", ") || "No files"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {r.actor} · rules v{r.rule_version ?? "-"} · {duration(r)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </Panel>
      <RunDetail run={run} />
    </div>
  );
}
