import { Eye, FileSpreadsheet, ListChecks } from "lucide-react";
import { useEffect, useState } from "react";

import { isImage } from "../../lib/api";
import { usePreview } from "../../lib/files";
import { useRun } from "../../lib/runs";
import DataGrid from "../ui/DataGrid";
import ImageViewer from "./ImageViewer";
import EmptyState from "../ui/EmptyState";
import Panel from "../ui/Panel";
import Tabs from "../ui/Tabs";
import RunResultView from "./RunResultView";
import type { SlotFile } from "./RunTab";

type View = "preview" | "result";

export default function OutputPanel({ selectedFile, runId }: { selectedFile: SlotFile | null; runId: string | null }) {
  const [view, setView] = useState<View>("preview");
  const { data: run } = useRun(runId);

  // A new run switches to its result; choosing another file switches back to the preview.
  useEffect(() => {
    if (runId) setView("result");
  }, [runId]);
  useEffect(() => {
    if (selectedFile) setView("preview");
  }, [selectedFile?.file.id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Panel
      scroll={false}
      title={view === "preview" ? (selectedFile?.file.original_name ?? "Preview") : "Result"}
      actions={
        runId && (
          <Tabs
            size="sm"
            value={view}
            onChange={setView}
            tabs={[
              { value: "preview", label: "Preview", icon: <Eye className="size-3.5" /> },
              { value: "result", label: "Result", icon: <ListChecks className="size-3.5" /> },
            ]}
          />
        )
      }
    >
      {view === "result" && run ? (
        <RunResultView run={run} />
      ) : selectedFile && isImage(selectedFile.file.original_name) ? (
        <ImageViewer key={selectedFile.file.id} file={selectedFile.file} />
      ) : (
        <FilePreview file={selectedFile} />
      )}
    </Panel>
  );
}

function FilePreview({ file }: { file: SlotFile | null }) {
  const [sheet, setSheet] = useState<string | null>(null);
  useEffect(() => setSheet(null), [file?.file.id]);
  const { data, isFetching, error } = usePreview(file?.file.id ?? null, sheet, file?.password || null);

  if (!file) {
    return (
      <EmptyState icon={<FileSpreadsheet className="size-5" />} title="No file selected">
        Upload a file on the left to see its contents here before running.
      </EmptyState>
    );
  }
  if (error) return <EmptyState title="Can't preview this file">{error.message}</EmptyState>;
  if (!data) return <div className="m-5 h-full animate-pulse rounded-[var(--radius)] bg-muted" />;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-2.5">
        {data.sheets.length > 1 ? (
          <Tabs
            size="sm"
            value={data.sheet}
            onChange={setSheet}
            tabs={data.sheets.map((s) => ({ value: s, label: s }))}
          />
        ) : (
          <span className="text-xs font-medium text-muted-foreground">Sheet: {data.sheet}</span>
        )}
        <span className="text-xs text-muted-foreground tabular-nums">
          {isFetching
            ? "Loading..."
            : data.rows.length < data.total_rows
              ? `First ${data.rows.length.toLocaleString()} of ${data.total_rows.toLocaleString()} rows`
              : `${data.total_rows.toLocaleString()} rows · ${data.columns.length} columns`}
        </span>
      </div>
      <div className="min-h-0 flex-1">
        <DataGrid columns={data.columns} rows={data.rows} />
      </div>
    </div>
  );
}
