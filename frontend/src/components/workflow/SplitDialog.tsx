import clsx from "clsx";
import { useEffect, useId, useRef, useState } from "react";

import { errorMessage } from "../../lib/api";
import { filsText, toFils, useSplitRun, type Split } from "../../lib/runs";
import Button from "../ui/Button";

type Props = { open: boolean; runId: string; split: Split; onClose: () => void };

const fieldClass =
  "min-h-11 w-full rounded-[var(--radius)] border border-border bg-card px-3 text-sm tabular-nums focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/**
 * Shown after a run that has an amount to split (the Causeway variance): put all of it on one
 * part, or type an amount for each. Confirm stays off until the parts add up to the total exactly.
 */
export default function SplitDialog({ open, runId, split, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const [amounts, setAmounts] = useState<Record<string, string>>(split.amounts);
  // The "All to ..." button last clicked; both stay plain until one is clicked, and typing clears it.
  const [chosen, setChosen] = useState<string | null>(null);
  const save = useSplitRun();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) {
      setAmounts(split.amounts);
      setChosen(null);
      save.reset();
      el.showModal();
    }
    if (!open && el.open) el.close();
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const total = toFils(split.total) ?? 0;
  const fils = split.parts.map((p) => toFils(amounts[p.key] ?? ""));
  const invalid = fils.some((f) => f === null);
  const left = total - fils.reduce<number>((sum, f) => sum + (f ?? 0), 0);

  const allTo = (key: string) => {
    setChosen(key);
    setAmounts(Object.fromEntries(split.parts.map((p) => [p.key, p.key === key ? split.total : "0.000"])));
  };
  const given = total - left;

  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      aria-labelledby={titleId}
      className="m-auto w-[min(520px,calc(100vw-32px))] rounded-[var(--radius-lg)] border border-border bg-card p-6 text-card-foreground shadow-md backdrop:bg-foreground/40"
    >
      <h2 id={titleId} className="text-base font-semibold">
        {split.title}
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">{split.message}</p>

      <div className="mt-4 flex items-baseline justify-between rounded-[var(--radius)] bg-warning-soft px-4 py-3">
        <span className="text-sm font-medium text-warning">Variance</span>
        <span className="text-xl font-semibold tabular-nums text-warning">{split.total} BHD</span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {split.parts.map((p) => (
          <Button
            key={p.key}
            variant={chosen === p.key ? "primary" : "secondary"}
            aria-pressed={chosen === p.key}
            onClick={() => allTo(p.key)}
          >
            All to {p.label}
          </Button>
        ))}
      </div>

      <div className="mt-4 grid gap-3">
        {split.parts.map((p, i) => (
          <label key={p.key} className="grid gap-1 text-sm font-medium">
            <span>
              {p.label} <span className="font-normal text-muted-foreground">{p.code}</span>
            </span>
            <input
              className={clsx(fieldClass, fils[i] === null && "border-destructive")}
              inputMode="decimal"
              value={amounts[p.key] ?? ""}
              onChange={(e) => {
                setChosen(null);
                setAmounts((a) => ({ ...a, [p.key]: e.target.value }));
              }}
            />
          </label>
        ))}
      </div>

      <div
        className={clsx(
          "mt-4 flex items-baseline justify-between rounded-[var(--radius)] px-4 py-4",
          invalid || left !== 0 ? "bg-destructive-soft text-destructive" : "bg-success-soft text-success",
        )}
      >
        <span className="text-base font-semibold">Total</span>
        <span className="text-2xl font-semibold tabular-nums">{invalid ? "-" : `${filsText(given)} BHD`}</span>
      </div>

      <p
        className={clsx(
          "mt-2 text-sm font-medium tabular-nums",
          invalid || left !== 0 ? "text-destructive" : "text-success",
        )}
        aria-live="polite"
      >
        {invalid
          ? "Enter amounts like 10.500 (up to 3 decimals)."
          : left === 0
            ? "The amounts add up to the variance."
            : left > 0
              ? `${filsText(left)} BHD still to assign.`
              : `${filsText(-left)} BHD more than the variance.`}
      </p>
      {save.error && <p className="mt-2 text-sm text-destructive">{errorMessage(save.error)}</p>}

      <div className="mt-6 flex flex-wrap justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Later
        </Button>
        <Button
          disabled={invalid || left !== 0 || save.isPending}
          onClick={() =>
            save.mutate(
              { runId, amounts: Object.fromEntries(split.parts.map((p, i) => [p.key, filsText(fils[i] ?? 0)])) },
              { onSuccess: onClose },
            )
          }
        >
          {save.isPending ? "Saving…" : "Confirm split"}
        </Button>
      </div>
    </dialog>
  );
}
