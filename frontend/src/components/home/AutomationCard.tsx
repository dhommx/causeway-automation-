import clsx from "clsx";
import { ArrowRight, Clock, Lock, Target, CalendarDays } from "lucide-react";
import type { CSSProperties } from "react";
import { Link } from "react-router-dom";

import { iconFor } from "../../constants/icons";
import type { Workflow } from "../../lib/api";

function CardBody({ wf }: { wf: Workflow }) {
  const Icon = iconFor(wf.icon);
  const facts = [
    { icon: Clock, label: "Today", value: wf.current_time },
    { icon: Target, label: "Target", value: wf.target_time },
    { icon: CalendarDays, label: "Runs", value: wf.frequency },
  ];
  return (
    <div className="flex h-full flex-col p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="grid size-12 place-items-center rounded-[var(--radius)] bg-accent-soft text-primary">
          <Icon className="size-6" aria-hidden />
        </div>
        <span className="text-3xl font-semibold text-border tabular-nums">{String(wf.number).padStart(2, "0")}</span>
      </div>
      <h2 className="mt-5 text-lg font-semibold text-foreground">{wf.name}</h2>
      <p className="mt-1.5 line-clamp-2 text-sm text-muted-foreground">{wf.summary}</p>
      <dl className="mt-auto grid grid-cols-3 gap-3 pt-5">
        {facts.map(({ icon: FactIcon, label, value }) => (
          <div key={label} className="min-w-0 rounded-[var(--radius)] bg-muted px-3 py-2">
            <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <FactIcon className="size-3.5" aria-hidden />
              {label}
            </dt>
            <dd className="mt-0.5 truncate text-sm font-medium text-foreground">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export default function AutomationCard({ wf, index }: { wf: Workflow; index: number }) {
  const style = { "--i": index } as CSSProperties;
  const frame = "enter relative flex min-h-[260px] flex-col overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card shadow-sm";

  if (wf.status !== "live") {
    return (
      <div className={frame} style={style} aria-disabled="true" aria-label={`${wf.name}, coming soon`}>
        <div className="pointer-events-none h-full opacity-70 blur-[3px] select-none" aria-hidden>
          <CardBody wf={wf} />
        </div>
        <div className="absolute inset-0 grid place-items-center bg-card/30">
          <div className="flex flex-col items-center gap-2 rounded-[var(--radius-lg)] bg-card/95 px-6 py-4 text-center shadow-md">
            <Lock className="size-5 text-muted-foreground" aria-hidden />
            <p className="text-sm font-semibold text-foreground">{wf.name}</p>
            <p className="text-xs text-muted-foreground">Coming soon</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <Link
      to={`/automations/${wf.key}`}
      style={style}
      className={clsx(
        frame,
        "group transition-[transform,box-shadow,border-color] duration-200 ease-out hover:-translate-y-0.5 hover:border-accent hover:shadow-md motion-reduce:transform-none",
      )}
    >
      <span className="absolute inset-x-0 top-0 h-1 bg-accent" aria-hidden />
      <CardBody wf={wf} />
      <div className="flex items-center justify-between border-t border-border px-6 py-3 text-sm font-medium text-primary">
        Open automation
        <ArrowRight className="size-4 transition-transform duration-200 group-hover:translate-x-1" aria-hidden />
      </div>
    </Link>
  );
}
