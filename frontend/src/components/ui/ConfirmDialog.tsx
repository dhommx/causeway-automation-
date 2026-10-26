import { useEffect, useId, useRef, type ReactNode } from "react";

import Button from "./Button";

type Props = {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
};

/**
 * A small modal question with two answers. Built on the native <dialog>, so focus stays inside
 * it and Esc counts as the cancel answer.
 */
export default function ConfirmDialog({ open, title, children, confirmLabel, cancelLabel, onConfirm, onCancel }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const confirm = useRef<HTMLButtonElement>(null);
  const titleId = useId();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) {
      el.showModal();
      confirm.current?.focus(); // the safe answer is focused, so Enter keeps the data
    }
    if (!open && el.open) el.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        onCancel();
      }}
      aria-labelledby={titleId}
      className="m-auto w-[min(440px,calc(100vw-32px))] rounded-[var(--radius-lg)] border border-border bg-card p-6 text-card-foreground shadow-md backdrop:bg-foreground/40"
    >
      <h2 id={titleId} className="text-base font-semibold">
        {title}
      </h2>
      <div className="mt-2 text-sm text-muted-foreground">{children}</div>
      <div className="mt-6 flex flex-wrap justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>
          {cancelLabel}
        </Button>
        <Button ref={confirm} onClick={onConfirm}>
          {confirmLabel}
        </Button>
      </div>
    </dialog>
  );
}
