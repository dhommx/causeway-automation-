import { CheckCircle2, X } from "lucide-react";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import { ToastContext, type ToastInput } from "./useToast";

type Toast = ToastInput & { id: number };

/** Short notices in the bottom corner. They close by themselves after a few seconds. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const notify = useCallback((t: ToastInput) => {
    setToasts((prev) => [...prev, { ...t, id: Date.now() + Math.random() }]);
  }, []);
  const dismiss = (id: number) => setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={notify}>
      {children}
      <div
        role="status"
        aria-live="polite"
        className="pointer-events-none fixed end-6 bottom-6 z-50 grid w-[min(380px,calc(100vw-2rem))] gap-2"
      >
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onClose={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000);
    return () => clearTimeout(timer);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      className="enter pointer-events-auto flex items-start gap-3 rounded-[var(--radius-lg)] border border-border bg-card p-4 shadow-md"
    >
      <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-foreground">{toast.title}</p>
        {toast.detail && <p className="mt-0.5 text-xs text-muted-foreground">{toast.detail}</p>}
      </div>
      <button
        type="button"
        aria-label="Close notification"
        onClick={onClose}
        className="-m-1 inline-flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground"
      >
        <X className="size-4" />
      </button>
    </div>
  );
}
