import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

import { iconFor } from "../../constants/icons";
import { WORKFLOW_TABS, type WorkflowTab } from "../../constants/workflowTabs";
import type { Workflow } from "../../lib/api";
import StatusPill from "../ui/StatusPill";
import Tabs from "../ui/Tabs";

export default function WorkflowHeader({
  wf,
  tab,
  onTab,
}: {
  wf: Workflow;
  tab: WorkflowTab;
  onTab: (t: WorkflowTab) => void;
}) {
  const Icon = iconFor(wf.icon);
  return (
    <div className="flex shrink-0 flex-wrap items-center justify-between gap-4">
      <div className="flex min-w-0 items-center gap-4">
        <Link
          to="/"
          aria-label="Back to automations"
          className="inline-flex size-11 shrink-0 items-center justify-center rounded-full border border-border bg-card text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground"
        >
          <ArrowLeft className="size-5" />
        </Link>
        <div className="grid size-11 shrink-0 place-items-center rounded-[var(--radius)] bg-accent-soft text-primary">
          <Icon className="size-5" aria-hidden />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Finance · {String(wf.number).padStart(2, "0")}</span>
            <StatusPill status={wf.status} />
            <span>v{wf.version}</span>
          </div>
          <h1 className="truncate text-xl font-semibold text-foreground">{wf.name}</h1>
        </div>
      </div>
      <Tabs tabs={WORKFLOW_TABS} value={tab} onChange={onTab} />
    </div>
  );
}
