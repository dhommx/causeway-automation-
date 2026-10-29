import { FolderOpen, RotateCcw, Save } from "lucide-react";
import { useEffect, useState } from "react";

import Button from "../components/ui/Button";
import Panel from "../components/ui/Panel";
import { useToast } from "../components/ui/useToast";
import { useSaveSettings, useSettings } from "../lib/settings";

const LAYOUT = `Data/
├── 2026-10-27/
│   └── Causeway Sales Reconciliation - 09-41-12/
│       ├── input/      files as uploaded + entries.json (typed values)
│       ├── output/     files the run produced
│       └── run.json    who, when, rules, status, file fingerprints
└── _uploads/           uploads not used yet (deleted after DAYS days)`;

export default function SettingsPage() {
  const { data } = useSettings();
  const save = useSaveSettings();
  const notify = useToast();
  const [folder, setFolder] = useState("");

  useEffect(() => {
    if (data) setFolder(data.data_folder);
  }, [data?.data_folder]); // eslint-disable-line react-hooks/exhaustive-deps

  const isDefault = data && data.data_folder === data.default_data_folder;
  const changed = data && folder.trim() !== data.data_folder;

  const submit = (value: string | null) =>
    save.mutate(
      { data_folder: value },
      { onSuccess: (s) => notify({ title: "Data folder saved", detail: s.data_folder }) },
    );

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-5">
      <div className="shrink-0">
        <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">Portal-wide settings. Every change is kept in the audit log.</p>
      </div>

      <Panel
        className="min-h-0 flex-1"
        title={
          <span className="inline-flex items-center gap-2">
            <FolderOpen className="size-4 text-primary" aria-hidden />
            Data folder
          </span>
        }
        footer={
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => submit(folder)} disabled={!changed || save.isPending}>
              <Save className="size-4" aria-hidden />
              Save folder
            </Button>
            <Button variant="secondary" onClick={() => submit(null)} disabled={isDefault || save.isPending}>
              <RotateCcw className="size-4" aria-hidden />
              Use default
            </Button>
            {save.error && <p className="w-full text-xs text-destructive">{save.error.message}</p>}
          </div>
        }
      >
        <div className="grid max-w-3xl gap-5 p-5">
          <p className="text-sm text-muted-foreground">
            Every run is saved here for audit: the files and images the user uploaded, the values they typed, and the
            files the portal produced. One folder per day, and one folder per run inside it.
          </p>

          <label className="grid gap-1.5 text-sm font-medium">
            Folder on the server
            <input
              value={folder}
              onChange={(e) => setFolder(e.target.value)}
              spellCheck={false}
              className="min-h-11 rounded-[var(--radius)] border border-border bg-card px-3 font-mono text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-describedby="folder-help"
            />
            <span id="folder-help" className="text-xs font-normal text-muted-foreground">
              A full path on the server running the portal, or a shared drive mounted on it.
              {data && <> Default: <span className="font-mono">{data.default_data_folder}</span>.</>} Changing it
              affects new uploads and runs only; older runs stay where they were saved.
            </span>
          </label>

          <section className="grid gap-2">
            <h3 className="text-sm font-semibold">What is saved</h3>
            <pre className="overflow-x-auto rounded-[var(--radius)] bg-muted p-4 text-xs leading-relaxed">
              {LAYOUT.replace("DAYS", String(data?.upload_keep_days ?? 7))}
            </pre>
          </section>
        </div>
      </Panel>
    </div>
  );
}
