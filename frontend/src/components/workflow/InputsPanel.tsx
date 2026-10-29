import clsx from "clsx";
import {
  AlertTriangle,
  CheckCircle2,
  FileSpreadsheet,
  Image as ImageIcon,
  Loader2,
  Play,
  X,
  XCircle,
} from "lucide-react";
import { useEffect, useState, type Dispatch, type SetStateAction } from "react";

import { isImage, type Schemas, type Workflow } from "../../lib/api";
import {
  describeUpload,
  type FileCheckState,
  formatBytes,
  sameValue,
  useFileChecks,
  useUploadFiles,
} from "../../lib/files";
import Button from "../ui/Button";
import ConfirmDialog from "../ui/ConfirmDialog";
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
  /** Values a file check wrote into manual fields; the user may change them (with a warning). */
  autoFilled: Record<string, string>;
  setAutoFilled: Dispatch<SetStateAction<Record<string, string>>>;
  selected: string | null;
  onSelect: (id: string) => void;
  onRun: () => void;
  running: boolean;
  runError: string | null;
};

/** The small line under a checked file: a tick when it passes, the reason when it does not. */
function FileCheckLine({ state, needsPassword }: { state: FileCheckState | undefined; needsPassword: boolean }) {
  if (needsPassword) return <p className="text-xs text-muted-foreground">Type the password to check the total.</p>;
  if (!state || state.pending)
    return (
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Loader2 className="size-3.5 animate-spin" aria-hidden />
        Checking the total...
      </p>
    );
  return (
    <p role="status" className={clsx("flex items-start gap-1.5 text-xs", state.ok ? "text-success" : "text-destructive")}>
      {state.ok ? (
        <CheckCircle2 className="mt-px size-3.5 shrink-0" aria-hidden />
      ) : (
        <XCircle className="mt-px size-3.5 shrink-0" aria-hidden />
      )}
      {state.message}
    </p>
  );
}

const fieldClass =
  "min-h-11 w-full rounded-[var(--radius)] border border-border bg-card px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export default function InputsPanel({
  wf,
  files,
  setFiles,
  params,
  setParams,
  autoFilled,
  setAutoFilled,
  selected,
  onSelect,
  onRun,
  running,
  runError,
}: Props) {
  const upload = useUploadFiles();
  const notify = useToast();

  // Files of `checked` slots are checked as soon as they are in (with their password, if any).
  const slotOf = (key: string) => wf.file_slots.find((s) => s.key === key);
  const checkedFiles = files.filter((f) => slotOf(f.slot)?.checked);
  const checks = useFileChecks(
    wf.key,
    checkedFiles
      .filter((f) => !slotOf(f.slot)?.password_protected || f.password)
      .map((f) => ({
        slot: f.slot,
        id: f.file.id,
        password: f.password,
        params: Object.fromEntries((slotOf(f.slot)?.check_params ?? []).map((k) => [k, params[k] ?? ""])),
      })),
  );
  const notPassed = checkedFiles.filter((f) => {
    const state = checks.get(f.file.id);
    return !state || state.pending || !state.ok;
  });
  const failed = notPassed.filter((f) => checks.get(f.file.id)?.pending === false);

  // What the passed checks found: values to write into manual fields, and a notice to show once.
  const fills: Record<string, string> = {};
  const fillSource: Record<string, string> = {};
  let notice: Schemas["NoticeOut"] | null = null;
  for (const f of checkedFiles) {
    const state = checks.get(f.file.id);
    if (!state || state.pending || !state.ok) continue;
    for (const [k, v] of Object.entries(state.fills ?? {})) {
      fills[k] = v;
      fillSource[k] = slotOf(f.slot)?.label ?? f.slot;
    }
    notice ??= state.notice ?? null;
  }

  // A new value from a check is written into its field (over what was there). A value the user
  // changed stays until the check finds something different.
  const fillsKey = JSON.stringify(fills);
  useEffect(() => {
    const found = JSON.parse(fillsKey) as Record<string, string>;
    const changed = Object.fromEntries(Object.entries(found).filter(([k, v]) => autoFilled[k] !== v));
    if (Object.keys(changed).length === 0) return;
    setParams((p) => ({ ...p, ...changed }));
    setAutoFilled((a) => ({ ...a, ...changed }));
  }, [fillsKey, autoFilled, setParams, setAutoFilled]);

  // The notice opens once for what it says; "Show transactions" opens it again.
  const noticeKey = notice ? JSON.stringify(notice) : null;
  const [dismissed, setDismissed] = useState<string | null>(null);

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
          {!runError && missing.length === 0 && failed.length > 0 && (
            <p className="text-xs text-destructive">
              Fix {failed.map((f) => slotOf(f.slot)?.label).join(", ")} before running: its check did not pass.
            </p>
          )}
          <Button
            onClick={onRun}
            disabled={missing.length > 0 || notPassed.length > 0 || running || upload.isPending}
            className="w-full"
          >
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
                    {(slot.password_protected || slot.checked) && (
                      <div className="grid gap-1.5 px-3 pb-3">
                        {slot.password_protected && (
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
                        )}
                        {slot.checked && (
                          <FileCheckLine state={checks.get(file.id)} needsPassword={slot.password_protected && !password} />
                        )}
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
                {autoFilled[m.key] !== undefined &&
                  (sameValue(params[m.key], autoFilled[m.key]) ? (
                    <span className="flex flex-wrap items-center gap-x-1.5 text-xs font-normal text-success">
                      <CheckCircle2 className="size-3.5 shrink-0" aria-hidden />
                      Filled in from the {fillSource[m.key] ?? "file"}.
                      {notice && (
                        <button
                          type="button"
                          onClick={() => setDismissed(null)}
                          className="cursor-pointer font-medium underline underline-offset-2"
                        >
                          Show transactions
                        </button>
                      )}
                    </span>
                  ) : (
                    <span role="alert" className="flex items-start gap-1.5 text-xs font-normal text-warning">
                      <AlertTriangle className="mt-px size-3.5 shrink-0" aria-hidden />
                      Changed from the {autoFilled[m.key]} BHD the system found. This does not match the file;
                      running with it is on your responsibility.
                    </span>
                  ))}
              </label>
            ))
          )}
        </section>
      </div>
      <ConfirmDialog
        open={noticeKey !== null && noticeKey !== dismissed}
        title={notice?.title ?? ""}
        confirmLabel="OK, understood"
        onConfirm={() => setDismissed(noticeKey)}
        onCancel={() => setDismissed(noticeKey)}
      >
        <p>{notice?.message}</p>
        {!!notice?.rows?.length && (
          <div className="mt-3 max-h-60 overflow-auto rounded-[var(--radius)] border border-border">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-muted text-foreground">
                <tr>
                  {(notice.columns ?? []).map((c) => (
                    <th key={c} className="px-2.5 py-1.5 text-start font-semibold">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {notice.rows.map((row, i) => (
                  <tr key={i} className="border-t border-border">
                    {row.map((cell, j) => (
                      <td key={j} className="px-2.5 py-1.5 tabular-nums">
                        {String(cell ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </ConfirmDialog>
    </Panel>
  );
}
