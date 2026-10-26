import { useState } from "react";
import { Navigate, useParams } from "react-router-dom";

import EmptyState from "../components/ui/EmptyState";
import HistoryTab from "../components/workflow/HistoryTab";
import RulesTab from "../components/workflow/RulesTab";
import RunTab from "../components/workflow/RunTab";
import WorkflowHeader from "../components/workflow/WorkflowHeader";
import type { WorkflowTab } from "../constants/workflowTabs";
import { errorMessage } from "../lib/api";
import { useWorkflow } from "../lib/workflows";

export default function WorkflowPage() {
  const { key = "" } = useParams();
  const { data: wf, isLoading, error } = useWorkflow(key);
  const [tab, setTab] = useState<WorkflowTab>("run");

  if (isLoading) return <div className="h-20 animate-pulse rounded-[var(--radius-lg)] bg-muted" />;
  if (error || !wf) {
    return <EmptyState title="Automation not found">{errorMessage(error, "This automation does not exist.")}</EmptyState>;
  }
  if (wf.status !== "live") return <Navigate to="/" replace />;

  // Tabs stay mounted (hidden, not removed) so uploads and a running job survive switching tabs.
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <WorkflowHeader wf={wf} tab={tab} onTab={setTab} />
      <div className="min-h-0 flex-1">
        <div className={tab === "run" ? "h-full" : "hidden"}>
          <RunTab wf={wf} />
        </div>
        <div className={tab === "history" ? "h-full" : "hidden"}>
          <HistoryTab wf={wf} />
        </div>
        <div className={tab === "rules" ? "h-full" : "hidden"}>
          <RulesTab wf={wf} />
        </div>
      </div>
    </div>
  );
}
