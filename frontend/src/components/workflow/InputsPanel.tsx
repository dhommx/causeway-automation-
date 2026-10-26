import clsx from "clsx";
import { FileSpreadsheet, Image as ImageIcon, Play, X } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";

import { isImage, type Workflow } from "../../lib/api";
import { describeUpload, formatBytes, useUploadFiles } from "../../lib/files";
import Button from "../ui/Button";
import Panel from "../ui/Panel";
import { useToast } from "../ui/useToast";
import FileDropzone from "./FileDropzone";
import type { SlotFile } from "./RunTab";

type Props = {
  wf: Workflow;
  files: SlotFile[];
  setFiles: Dispatch<SetStateAction<SlotFile[]>>;
  params: Record<string, string>;
  setParams: Dispatch<SetStateAction<Record<string, string>>>;
  selected: string | null;
  onSelect: (id: string) => void;
  onRun: () => void;
  running: boolean;
  runError: string | null;
};

const fieldClass =
  "min-h-11 w-full rounded-[var(--radius)] border border-border bg-card px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export default function InputsPanel({
  wf,
  files,
  setFiles,
  params,
  setParams,
  selected,
  onSelect,
  onRun,
  running,
  runError,
}: Props) {
  const upload = useUploadFiles();
  const notify = useToast();

  const missing = [
    ...wf.file_slots.filter((s) => s.required && !files.some((f) => f.slot === s.key)).map((s) => s.label),
    ...wf.manual_fields.filter((m) => m.required && !params[m.key]).map((m) => m.label),
  ];

  const addFiles = (slot: string, multiple: boolean, picked: File[]) =>
    upload.mutate(picked, {
      onSuccess: (stored) => {
        const added = stored.map((file) => ({ slot, file, password: "" }));
        setFiles((prev) => [...(multiple ? prev : prev.filter((f) => f.slot !== slot)), ...added]);
        onSelect(stored[0].id);
        notify(describeUpload(stored));
      },
    });

  return (
    <Panel
      title="Inputs"
      footer={
        <div className="grid gap-2">
          {runError && <p className="text-xs text-destructive">{runError}</p>}
          {!runError && missing.length > 0 && (
            <p className="text-xs text-muted-foreground">Needed: {missing.join(", ")}</p>
          )}
          <Button onClick={onRun} disabled={missing.length > 0 || running || upload.isPending} className="w-full">
            <Play className="size-4" aria-hidden />
            {running ? "Starting..." : "Run automation"}
          </Button>
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-6 p-5">
        {wf.file_slots.map((slot) => {
          const slotFiles = files.filter((f) => f.slot === slot.key);
          return (
            <section key={slot.key} className="grid grid-cols-1 gap-2.5">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  {slot.label}
                  {slot.required && <span className="text-destructive"> *</span>}
                </h3>
                {slot.help && <p className="text-xs text-muted-foreground">{slot.help}</p>}
              </div>
              <FileDropzone
                accept={slot.accept}
                multiple={slot.multiple}
                busy={upload.isPending}
                onFiles={(picked) => addFiles(slot.key, slot.multiple, picked)}
              />
              {upload.error && <p className="text-xs text-destructive">{upload.error.message}</p>}
              <ul className="grid grid-cols-1 gap-1.5">
                {slotFiles.map(({ file, password }) => (
                  <li
                    key={file.id}
                    className={clsx(
                      "rounded-[var(--radius)] border transition-colors duration-150",
                      selected === file.id ? "border-accent bg-accent-soft" : "border-border bg-card hover:bg-muted",
                    )}
                  >
                    <div className="flex items-center gap-2 pe-1">
                      <button
                        type="button"
                        onClick={() => onSelect(file.id)}
                        className="flex min-h-11 min-w-0 flex-1 cursor-pointer items-center gap-2.5 ps-3 text-start"
                        title="Show in preview"
                      >
                        {isImage(file.original_name) ? (
                          <ImageIcon className="size-4 shrink-0 text-primary" aria-hidden />
                        ) : (
                          <FileSpreadsheet className="size-4 shrink-0 text-success" aria-hidden />
                        )}
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">{file.original_name}</span>
                          <span className="block text-xs text-muted-foreground">{formatBytes(file.size_bytes)}</span>
                        </span>
                      </button>
                      <button
                        type="button"
                        aria-label={`Remove ${file.original_name}`}
                        onClick={() => setFiles((prev) => prev.filter((f) => f.file.id !== file.id))}
                        className="inline-flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-full text-muted-foreground hover:bg-card hover:text-foreground"
                      >
                        <X className="size-4" />
                      </button>
                    </div>
                    {slot.password_protected && (
                      <div className="px-3 pb-3">
                        <input
                          type="password"
                          placeholder="File password"
                          value={password}
                          onChange={(e) =>
                            setFiles((prev) =>
                              prev.map((f) => (f.file.id === file.id ? { ...f, password: e.target.value } : f)),
                            )
                          }
                          className={fieldClass}
                        />
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          );
        })}

        <section className="grid grid-cols-1 gap-2.5">
          <h3 className="text-sm font-semibold text-foreground">Manual entries</h3>
          {wf.manual_fields.length === 0 ? (
            <p className="rounded-[var(--radius)] bg-muted px-3 py-2.5 text-xs text-muted-foreground">
              No manual entries for this automation yet. They are added when its steps are defined.
            </p>
          ) : (
            wf.manual_fields.map((m) => (
              <label key={m.key} className="grid gap-1.5 text-sm font-medium">
                <span>
                  {m.label}
                  {m.required && <span className="text-destructive"> *</span>}
                </span>
                {m.type === "select" ? (
                  <select
                    className={fieldClass}
                    value={params[m.key] ?? ""}
                    onChange={(e) => setParams((p) => ({ ...p, [m.key]: e.target.value }))}
                  >
                    <option value="">Choose...</option>
                    {m.options.map((o) => (
                      <option key={o}>{o}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    className={clsx(fieldClass, (m.type === "number" || m.type === "money") && "tabular-nums")}
                    type={m.type === "date" ? "date" : "text"}
                    inputMode={m.type === "number" || m.type === "money" ? "decimal" : undefined}
                    value={params[m.key] ?? ""}
                    onChange={(e) => setParams((p) => ({ ...p, [m.key]: e.target.value }))}
                  />
                )}
                {m.help && <span className="text-xs font-normal text-muted-foreground">{m.help}</span>}
              </label>
            ))
          )}
        </section>
      </div>
    </Panel>
  );
}
