import { Download, FileSpreadsheet, Image as ImageIcon, ScrollText } from "lucide-react";
import { useState } from "react";

import { downloadUrl, isImage, type Run } from "../../lib/api";
import { formatBytes } from "../../lib/files";
import { formatDateTime, useRunAudit } from "../../lib/runs";
import EmptyState from "../ui/EmptyState";
import Panel from "../ui/Panel";
import Tabs from "../ui/Tabs";
import RunResultView from "./RunResultView";

type View = "result" | "record";

export default function RunDetail({ run }: { run: Run | null }) {
  const [view, setView] = useState<View>("result");

  if (!run) {
    return (
      <Panel title="Run details">
        <EmptyState icon={<ScrollText className="size-5" />} title="Choose a run">
          Its inputs, outputs, rules and audit trail appear here.
        </EmptyState>
      </Panel>
    );
  }

  return (
    <Panel
      scroll={view === "record"}
      title={`Run ${run.id.slice(0, 8)}`}
      actions={
        <Tabs
          size="sm"
          value={view}
          onChange={setView}
          tabs={[
            { value: "result", label: "Result" },
            { value: "record", label: "Audit record" },
          ]}
        />
      }
    >
      {view === "result" ? <RunResultView key={run.id} run={run} /> : <AuditRecord run={run} />}
    </Panel>
  );
}

function AuditRecord({ run }: { run: Run }) {
  const { data: events } = useRunAudit(run.id);
  const facts: [string, string][] = [
    ["Run ID", run.id],
    ["Started by", run.actor],
    ["Trigger", run.trigger],
    ["Created", formatDateTime(run.created_at)],
    ["Started", formatDateTime(run.started_at)],
    ["Finished", formatDateTime(run.finished_at)],
    ["Workflow version", run.workflow_version],
    ["Rules version", String(run.rule_version ?? "-")],
  ];
  const params = Object.entries(run.params ?? {});

  return (
    <div className="grid gap-6 p-5">
      <dl className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-x-6 gap-y-3">
        {facts.map(([k, v]) => (
          <div key={k}>
            <dt className="text-xs text-muted-foreground">{k}</dt>
            <dd className="truncate text-sm font-medium tabular-nums" title={v}>{v}</dd>
          </div>
        ))}
      </dl>

      <section className="grid gap-2">
        <h3 className="text-sm font-semibold">Files</h3>
        <ul className="grid gap-1.5">
          {run.files.map((f) => (
            <li key={f.file.id} className="flex items-center gap-3 rounded-[var(--radius)] border border-border px-3 py-2">
              {isImage(f.file.original_name) ? (
                <ImageIcon className="size-4 shrink-0 text-primary" aria-hidden />
              ) : (
                <FileSpreadsheet className="size-4 shrink-0 text-success" aria-hidden />
              )}
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{f.file.original_name}</span>
                <span className="block truncate text-xs text-muted-foreground">
                  {f.role === "input" ? `Input · ${f.slot}` : "Output"} · {formatBytes(f.file.size_bytes)} · SHA-256{" "}
                  {f.file.sha256.slice(0, 12)}
                </span>
              </span>
              <a
                href={downloadUrl(f.file.id)}
                aria-label={`Download ${f.file.original_name}`}
                className="inline-flex size-9 items-center justify-center rounded-full text-primary hover:bg-primary/10"
              >
                <Download className="size-4" />
              </a>
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-2">
        <h3 className="text-sm font-semibold">Manual entries</h3>
        {params.length === 0 ? (
          <p className="text-xs text-muted-foreground">None.</p>
        ) : (
          <dl className="grid grid-cols-2 gap-2 text-sm">
            {params.map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs text-muted-foreground">{k}</dt>
                <dd className="font-medium tabular-nums">{String(v)}</dd>
              </div>
            ))}
          </dl>
        )}
      </section>

      <section className="grid gap-2">
        <h3 className="text-sm font-semibold">Audit trail</h3>
        <ol className="grid gap-2 border-s border-border ps-4">
          {events?.map((e) => (
            <li key={e.id} className="text-sm">
              <span className="font-medium">{e.action}</span>
              <span className="text-muted-foreground"> · {e.actor} · {formatDateTime(e.at)}</span>
            </li>
          ))}
        </ol>
      </section>

      {(run.result as { log?: string[] } | null)?.log?.length ? (
        <section className="grid gap-2">
          <h3 className="text-sm font-semibold">Processing log</h3>
          <pre className="rounded-[var(--radius)] bg-muted p-3 text-xs whitespace-pre-wrap">
            {((run.result as { log: string[] }).log).join("\n")}
          </pre>
        </section>
      ) : null}
    </div>
  );
}
