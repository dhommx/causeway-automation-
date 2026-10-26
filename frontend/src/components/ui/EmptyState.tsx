import type { ReactNode } from "react";

export default function EmptyState({
  icon,
  title,
  children,
  action,
}: {
  icon?: ReactNode;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="grid h-full place-items-center p-8">
      <div className="grid max-w-sm justify-items-center gap-3 text-center">
        {icon && <div className="grid size-12 place-items-center rounded-full bg-muted text-muted-foreground">{icon}</div>}
        <p className="font-medium text-foreground">{title}</p>
        {children && <p className="text-sm text-muted-foreground">{children}</p>}
        {action}
      </div>
    </div>
  );
}
