import clsx from "clsx";
import { Save, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";

import type { RuleSet, Workflow } from "../../lib/api";
import { useRules, useSaveRules } from "../../lib/rules";
import { formatDateTime } from "../../lib/runs";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import Panel from "../ui/Panel";

/**
 * Rules are the values and conditions an automation uses (rates, codes, filters). Saving always
 * makes a new version; each run records the version it used. A dedicated form per automation
 * replaces the raw JSON editor once that automation's rules are defined.
 */
export default function RulesTab({ wf }: { wf: Workflow }) {
  const { data } = useRules(wf.key);
  const save = useSaveRules(wf.key);
  const [viewing, setViewing] = useState<RuleSet | null>(null);
  const [text, setText] = useState("{}");
  const [note, setNote] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);

  const current = data?.current;
  const shown = viewing ?? current ?? null;
  const isCurrent = !viewing || viewing.id === current?.id;

  useEffect(() => {
    if (shown) setText(JSON.stringify(shown.values, null, 2));
  }, [shown?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = () => {
    let values: Record<string, unknown>;
    try {
      values = JSON.parse(text);
      if (typeof values !== "object" || values === null || Array.isArray(values)) throw new Error();
    } catch {
      setParseError("Rules must be a JSON object, for example {}.");
      return;
    }
    setParseError(null);
    save.mutate({ values, note }, { onSuccess: () => { setNote(""); setViewing(null); } });
  };

  const empty = shown && Object.keys(shown.values).length === 0;

  return (
    <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[1fr_minmax(280px,340px)]">
      <Panel
        scroll={false}
        title={shown ? `Rules · version ${shown.version}${isCurrent ? " (current)" : ""}` : "Rules"}
        footer={
          isCurrent ? (
            <div className="flex flex-wrap items-center gap-3">
              <input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="What changed? (saved with the version)"
                className="min-h-11 min-w-0 flex-1 rounded-[var(--radius)] border border-border bg-card px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <Button onClick={submit} disabled={save.isPending}>
                <Save className="size-4" aria-hidden />
                Save as new version
              </Button>
              {(parseError || save.error) && (
                <p className="w-full text-xs text-destructive">{parseError ?? save.error?.message}</p>
              )}
            </div>
          ) : (
            <Button variant="secondary" onClick={() => setViewing(null)}>
              Back to current version
            </Button>
          )
        }
      >
        <div className="flex min-h-0 flex-1 flex-col gap-3 p-5">
          {empty && isCurrent && (
            <div className="shrink-0 rounded-[var(--radius)] bg-muted px-4 py-3 text-sm text-muted-foreground">
              <SlidersHorizontal className="me-2 inline size-4" aria-hidden />
              No rules are set for this automation yet. They will be added when its steps are defined.
            </div>
          )}
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            readOnly={!isCurrent}
            spellCheck={false}
            aria-label="Rules (JSON)"
            className="scroll-area min-h-0 flex-1 resize-none rounded-[var(--radius)] border border-border bg-muted/40 p-4 font-mono text-[13px] leading-relaxed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
      </Panel>

      <Panel title="Versions">
        {!data ? (
          <div className="m-5 h-24 animate-pulse rounded-[var(--radius)] bg-muted" />
        ) : data.versions.length === 0 ? (
          <EmptyState title="No versions" />
        ) : (
          <ul className="divide-y divide-border">
            {data.versions.map((v) => (
              <li key={v.id}>
                <button
                  type="button"
                  onClick={() => setViewing(v.id === current?.id ? null : v)}
                  className={clsx(
                    "grid w-full cursor-pointer gap-0.5 border-s-[3px] px-5 py-3 text-start transition-colors duration-150",
                    shown?.id === v.id ? "border-accent bg-accent-soft/60" : "border-transparent hover:bg-muted",
                  )}
                >
                  <span className="text-sm font-medium">
                    Version {v.version}
                    {v.id === current?.id && <span className="ms-2 text-xs text-success">current</span>}
                  </span>
                  <span className="truncate text-xs text-muted-foreground">{v.note || "No note"}</span>
                  <span className="text-xs text-muted-foreground">
                    {v.actor} · {formatDateTime(v.created_at)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
