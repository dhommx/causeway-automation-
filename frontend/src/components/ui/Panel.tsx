import clsx from "clsx";
import type { ReactNode } from "react";

type Props = {
  title?: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
  /** The body scrolls by default. Turn off for content that fills the body itself (e.g. a grid). */
  scroll?: boolean;
  bodyClassName?: string;
};

/**
 * The building block of every page: a card with a fixed header and footer and a body that
 * scrolls on its own. Pages never scroll; panels do.
 */
export default function Panel({ title, actions, footer, children, className, scroll = true, bodyClassName }: Props) {
  return (
    <section
      className={clsx(
        "flex min-h-0 flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card shadow-sm",
        className,
      )}
    >
      {(title || actions) && (
        <header className="flex min-h-14 shrink-0 items-center justify-between gap-3 border-b border-border px-5">
          <h2 className="truncate text-sm font-semibold text-foreground">{title}</h2>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={clsx("min-h-0 flex-1", scroll ? "scroll-area" : "flex flex-col", bodyClassName)}>
        {children}
      </div>
      {footer && <footer className="shrink-0 border-t border-border px-5 py-3">{footer}</footer>}
    </section>
  );
}
