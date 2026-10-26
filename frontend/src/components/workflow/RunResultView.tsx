import { AlertTriangle, Download, Loader2, XCircle } from "lucide-react";
import { useState } from "react";

import { downloadUrl, type Run } from "../../lib/api";
import { formatBytes } from "../../lib/files";
import { duration, isFinished } from "../../lib/runs";
import DataGrid from "../ui/DataGrid";
import EmptyState from "../ui/EmptyState";
import MetricTile from "../ui/MetricTile";
import StatusPill from "../ui/StatusPill";
import Tabs from "../ui/Tabs";

type Metric = { label: string; value: string; tone?: string };
type Table = { title: string; columns: string[]; rows: unknown[][] };

/** What a run produced: metrics, warnings, output files and result tables. */
export default function RunResultView({ run }: { run: Run }) {
  const [tableIndex, setTableIndex] = useState("0");

  if (!isFinished(run)) {
    return (
      <EmptyState icon={<Loader2 className="size-5 animate-spin" />} title={run.status === "queued" ? "Waiting to start" : "Processing"}>
        The automation is running. This page updates by itself.
      </EmptyState>
    );
  }
  if (run.status === "failed") {
    return (
      <EmptyState icon={<XCircle className="size-5 text-destructive" />} title="The run failed">
        {run.error}
      </EmptyState>
    );
  }

  const result = (run.result ?? {}) as { metrics?: Metric[]; tables?: Table[]; warnings?: string[] };
  const outputs = run.files.filter((f) => f.role === "output");
  const tables = result.tables ?? [];
  const table = tables[Number(tableIndex)] ?? tables[0];

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="grid shrink-0 gap-3 border-b border-border p-5">
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <StatusPill status={run.status} />
          <span>Took {duration(run)}</span>
          <span>Rules v{run.rule_version ?? "-"}</span>
        </div>
        {!!result.metrics?.length && (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-3">
            {result.metrics.map((m) => (
              <MetricTile key={m.label} label={m.label} value={m.value} tone={m.tone} />
            ))}
          </div>
        )}
        {result.warnings?.map((w) => (
          <p key={w} className="flex items-start gap-2 rounded-[var(--radius)] bg-warning-soft px-3 py-2 text-xs text-warning">
            <AlertTriangle className="mt-px size-3.5 shrink-0" aria-hidden />
            {w}
          </p>
        ))}
        {outputs.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {outputs.map((o) => (
              <a
                key={o.file.id}
                href={downloadUrl(o.file.id)}
                className="inline-flex min-h-11 items-center gap-2 rounded-[var(--radius)] bg-primary px-4 text-sm font-semibold text-on-primary shadow-sm transition-[transform,background-color] duration-200 hover:-translate-y-px hover:bg-primary-hover"
              >
                <Download className="size-4" aria-hidden />
                {o.file.original_name}
                <span className="font-normal text-on-primary/70">{formatBytes(o.file.size_bytes)}</span>
              </a>
            ))}
          </div>
        )}
      </div>
      {table ? (
        <div className="flex min-h-0 flex-1 flex-col">
          {tables.length > 1 && (
            <div className="shrink-0 border-b border-border px-5 py-2.5">
              <Tabs
                size="sm"
                value={tableIndex}
                onChange={setTableIndex}
                tabs={tables.map((t, i) => ({ value: String(i), label: t.title }))}
              />
            </div>
          )}
          <div className="min-h-0 flex-1">
            <DataGrid columns={table.columns} rows={table.rows} />
          </div>
        </div>
      ) : (
        <EmptyState title="No tables in this result" />
      )}
    </div>
  );
}
