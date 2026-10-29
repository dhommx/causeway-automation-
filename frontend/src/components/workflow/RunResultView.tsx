import { AlertTriangle, CalendarDays, Download, Loader2, Scale, XCircle } from "lucide-react";
import clsx from "clsx";
import { useState } from "react";

import { downloadUrl, type Run } from "../../lib/api";
import { formatBytes } from "../../lib/files";
import { duration, isFinished, type Split } from "../../lib/runs";
import Button from "../ui/Button";
import DataGrid from "../ui/DataGrid";
import EmptyState from "../ui/EmptyState";
import MetricTile from "../ui/MetricTile";
import StatusPill from "../ui/StatusPill";
import Tabs from "../ui/Tabs";
import SplitDialog from "./SplitDialog";

type Metric = { label: string; value: string; tone?: string };
type Table = { title: string; columns: string[]; rows: unknown[][]; note?: string; note_tone?: string; file?: string };
type Output = Run["files"][number];

function DownloadButton({ output, compact = false }: { output: Output; compact?: boolean }) {
  return (
    <a
      href={downloadUrl(output.file.id)}
      className={clsx(
        "inline-flex min-h-11 shrink-0 items-center gap-2 rounded-[var(--radius)] bg-primary px-4 text-sm font-semibold text-on-primary shadow-sm transition-[transform,background-color] duration-200 hover:-translate-y-px hover:bg-primary-hover",
        compact && "self-start",
      )}
    >
      <Download className="size-4" aria-hidden />
      {output.file.original_name}
      <span className="font-normal text-on-primary/70">{formatBytes(output.file.size_bytes)}</span>
    </a>
  );
}

/**
 * What a run produced: metrics, warnings, output files and result tables.
 * autoSplit opens an unconfirmed split by itself (only the Run tab does this; tabs stay mounted,
 * so two views opening it would stack two modals).
 */
export default function RunResultView({ run, autoSplit = false }: { run: Run; autoSplit?: boolean }) {
  const [tableIndex, setTableIndex] = useState("0");
  // An unconfirmed split opens by itself once per run (if autoSplit); "Later" closes it.
  const [splitOpen, setSplitOpen] = useState<boolean | null>(null);

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

  const result = (run.result ?? {}) as { metrics?: Metric[]; tables?: Table[]; warnings?: string[]; split?: Split | null };
  const split = result.split ?? null;
  const showSplit = !!split && (splitOpen ?? (autoSplit && !split.confirmed));
  const tables = result.tables ?? [];
  const table = tables[Number(tableIndex)] ?? tables[0];
  // A file that belongs to a tab (its ERP upload file) is offered on that tab, not up here.
  const tabFiles = new Set(tables.map((t) => t.file).filter(Boolean));
  const allOutputs = run.files.filter((f) => f.role === "output");
  const outputs = allOutputs.filter((f) => !tabFiles.has(f.file.original_name));
  const tableOutput = table?.file ? allOutputs.find((f) => f.file.original_name === table.file) : undefined;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="grid shrink-0 gap-3 border-b border-border p-5">
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <StatusPill status={run.status} />
          <span>Took {duration(run)}</span>
          <span>Rules v{run.rule_version ?? "-"}</span>
        </div>
        {!!result.metrics?.length && (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
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
        {split && (
          <div className="flex flex-wrap items-center gap-3">
            <Button variant={split.confirmed ? "secondary" : "primary"} onClick={() => setSplitOpen(true)}>
              <Scale className="size-4" aria-hidden />
              {split.confirmed ? "Change variance split" : "Split the variance"}
            </Button>
            <span className={clsx("text-sm", split.confirmed ? "text-muted-foreground" : "font-medium text-warning")}>
              {split.confirmed
                ? split.parts.map((p) => `${p.label} ${split.amounts[p.key]}`).join(" · ")
                : `Variance ${split.total} BHD not split yet`}
            </span>
            <SplitDialog open={showSplit} runId={run.id} split={split} onClose={() => setSplitOpen(false)} />
          </div>
        )}
        {outputs.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {outputs.map((o) => (
              <DownloadButton key={o.file.id} output={o} />
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
          {tableOutput && (
            <div className="mx-5 mt-3 flex shrink-0 flex-wrap items-center gap-3">
              <DownloadButton output={tableOutput} />
              <span className="text-xs text-muted-foreground">ERP upload file for this tab. Doc No is left for you to type in PACT.</span>
            </div>
          )}
          {table.note && (
            <p
              className={clsx(
                "mx-5 mt-3 flex shrink-0 items-center gap-2 rounded-[var(--radius)] px-3 py-2 text-sm font-semibold",
                table.note_tone === "warn" ? "bg-warning-soft text-warning" : "bg-accent-soft text-primary",
              )}
            >
              {table.note_tone === "warn" ? (
                <AlertTriangle className="size-4 shrink-0" aria-hidden />
              ) : (
                <CalendarDays className="size-4 shrink-0" aria-hidden />
              )}
              {table.note}
            </p>
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
