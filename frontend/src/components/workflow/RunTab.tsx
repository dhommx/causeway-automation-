import { useEffect, useState } from "react";

import type { StoredFile, Workflow } from "../../lib/api";
import { useCreateRun } from "../../lib/runs";
import ConfirmDialog from "../ui/ConfirmDialog";
import InputsPanel from "./InputsPanel";
import OutputPanel from "./OutputPanel";

export type SlotFile = { slot: string; file: StoredFile; password: string };

/**
 * The run screen's work is saved in this browser tab (sessionStorage) as it changes, so a refresh
 * can offer to bring it back. File passwords are never saved; they are typed again after a restore.
 * The files themselves are already stored on the server; only their details are kept here.
 */
type Draft = {
  files: { slot: string; file: StoredFile }[];
  params: Record<string, string>;
  selected: string | null;
  runId: string | null;
};

/** How a typed value is shown in the confirm box: dates as DD/MM/YYYY, money with 3 decimals. */
function shown(type: string, value: string | undefined): string {
  const v = (value ?? "").trim();
  if (!v) return "Not entered";
  if (type === "date") {
    const [y, m, d] = v.split("-");
    return d ? `${d}/${m}/${y}` : v;
  }
  if (type === "money" && /^-?\d*(\.\d*)?$/.test(v)) {
    const [whole, frac = ""] = v.split(".");
    return `${whole || "0"}.${(frac + "000").slice(0, Math.max(3, frac.length))} BHD`;
  }
  return v;
}

const draftKey = (workflowKey: string) => `run-draft:${workflowKey}`;

function readDraft(workflowKey: string): Draft | null {
  try {
    const raw = sessionStorage.getItem(draftKey(workflowKey));
    if (!raw) return null;
    const d = JSON.parse(raw) as Draft;
    const hasWork = d.files.length > 0 || Object.values(d.params).some(Boolean) || d.runId;
    return hasWork ? d : null;
  } catch {
    return null;
  }
}

function writeDraft(workflowKey: string, draft: Draft) {
  try {
    sessionStorage.setItem(draftKey(workflowKey), JSON.stringify(draft));
  } catch {
    // Storage blocked or full: refresh just starts empty, as before.
  }
}

function clearDraft(workflowKey: string) {
  try {
    sessionStorage.removeItem(draftKey(workflowKey));
  } catch {
    // nothing to clear
  }
}

export default function RunTab({ wf }: { wf: Workflow }) {
  const [files, setFiles] = useState<SlotFile[]>([]);
  const [params, setParams] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  // "Expand" gives the preview/result the full width by hiding the inputs (they stay mounted).
  const [expanded, setExpanded] = useState(false);
  // Work saved before a refresh, waiting for the user to keep or discard it.
  const [pending, setPending] = useState<Draft | null>(() => readDraft(wf.key));
  // Run is pressed: the typed values are shown for a last check before the run starts.
  const [confirming, setConfirming] = useState(false);
  const createRun = useCreateRun();

  // Save as the user works. Not while the keep/discard question is open, or the empty screen
  // would overwrite the saved work before they answer.
  useEffect(() => {
    if (pending) return;
    writeDraft(wf.key, { files: files.map(({ slot, file }) => ({ slot, file })), params, selected, runId });
  }, [wf.key, pending, files, params, selected, runId]);

  const keep = () => {
    if (!pending) return;
    setFiles(pending.files.map((f) => ({ ...f, password: "" })));
    setParams(pending.params);
    setSelected(pending.selected);
    setRunId(pending.runId);
    setPending(null);
  };
  const discard = () => {
    clearDraft(wf.key);
    setPending(null);
  };

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
  const needsPassword = pending?.files.some((f) => wf.file_slots.find((s) => s.key === f.slot)?.password_protected);

  return (
    <div className={expanded ? "grid h-full min-h-0" : "grid h-full min-h-0 gap-4 lg:grid-cols-[minmax(320px,380px)_1fr]"}>
      <div className={expanded ? "hidden" : "contents"}>
        <InputsPanel
          wf={wf}
          files={files}
          setFiles={setFiles}
          params={params}
          setParams={setParams}
          selected={selected}
          onSelect={setSelected}
          onRun={() => (wf.manual_fields.length ? setConfirming(true) : start())}
          running={createRun.isPending}
          runError={createRun.error?.message ?? null}
        />
      </div>
      <OutputPanel
        selectedFile={selectedFile}
        runId={runId}
        expanded={expanded}
        onToggleExpanded={() => setExpanded((e) => !e)}
      />
      <ConfirmDialog
        open={confirming}
        title="Are these values correct?"
        confirmLabel="Yes, run"
        cancelLabel="Go back and edit"
        onConfirm={() => {
          setConfirming(false);
          start();
        }}
        onCancel={() => setConfirming(false)}
      >
        <p>Check the values you typed before the automation runs.</p>
        <dl className="mt-4 grid gap-2 rounded-[var(--radius)] border border-border bg-muted/50 p-4">
          {wf.manual_fields.map((m) => (
            <div key={m.key} className="flex items-baseline justify-between gap-4">
              <dt className="text-muted-foreground">{m.label}</dt>
              <dd className="text-base font-semibold text-foreground tabular-nums">{shown(m.type, params[m.key])}</dd>
            </div>
          ))}
        </dl>
      </ConfirmDialog>
      <ConfirmDialog
        open={pending !== null}
        title="Keep your previous work?"
        confirmLabel="Keep my data"
        cancelLabel="Start fresh"
        onConfirm={keep}
        onCancel={discard}
      >
        <p>
          The page was refreshed. Keep the files, entries and result you had
          {pending?.files.length ? ` (${pending.files.length} file${pending.files.length > 1 ? "s" : ""})` : ""}, or
          start with an empty screen?
        </p>
        {needsPassword && <p className="mt-2">File passwords are not kept, so type them again after keeping.</p>}
      </ConfirmDialog>
    </div>
  );
}
