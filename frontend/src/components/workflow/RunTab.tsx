import { useState } from "react";

import type { StoredFile, Workflow } from "../../lib/api";
import { useCreateRun } from "../../lib/runs";
import InputsPanel from "./InputsPanel";
import OutputPanel from "./OutputPanel";

export type SlotFile = { slot: string; file: StoredFile; password: string };

export default function RunTab({ wf }: { wf: Workflow }) {
  const [files, setFiles] = useState<SlotFile[]>([]);
  const [params, setParams] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const createRun = useCreateRun();

  const start = () => {
    const inputs: Record<string, { id: string; password?: string | null }[]> = {};
    for (const f of files) {
      (inputs[f.slot] ??= []).push({ id: f.file.id, password: f.password || null });
    }
    createRun.mutate(
      { workflow_key: wf.key, inputs, params },
      { onSuccess: (run) => setRunId(run.id) },
    );
  };

  const selectedFile = files.find((f) => f.file.id === selected) ?? null;

  return (
    <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[minmax(320px,380px)_1fr]">
      <InputsPanel
        wf={wf}
        files={files}
        setFiles={setFiles}
        params={params}
        setParams={setParams}
        selected={selected}
        onSelect={setSelected}
        onRun={start}
        running={createRun.isPending}
        runError={createRun.error?.message ?? null}
      />
      <OutputPanel selectedFile={selectedFile} runId={runId} />
    </div>
  );
}
