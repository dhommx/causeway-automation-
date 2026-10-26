import { LayoutGrid } from "lucide-react";

import AutomationCard from "../components/home/AutomationCard";
import EmptyState from "../components/ui/EmptyState";
import { errorMessage } from "../lib/api";
import { useDepartments } from "../lib/workflows";

export default function HomePage() {
  const { data, isLoading, error } = useDepartments();
  const finance = data?.find((d) => d.key === "finance");
  const workflows = finance?.workflows ?? [];
  const live = workflows.filter((w) => w.status === "live").length;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-5">
      <div className="flex shrink-0 flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Finance automations</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Pick an automation to upload its files, run it and download the result.
          </p>
        </div>
        {workflows.length > 0 && (
          <p className="text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">{live}</span> of {workflows.length} live
          </p>
        )}
      </div>

      <div className="scroll-area -m-1 min-h-0 flex-1 p-1">
        {isLoading && (
          <div className="grid gap-5 lg:h-full lg:grid-cols-2 lg:grid-rows-2">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="min-h-[260px] animate-pulse rounded-[var(--radius-lg)] bg-muted" />
            ))}
          </div>
        )}
        {error && (
          <EmptyState icon={<LayoutGrid className="size-5" />} title="Could not load automations">
            {errorMessage(error)} Check that the API is running.
          </EmptyState>
        )}
        {!isLoading && !error && (
          <div className="grid gap-5 lg:h-full lg:grid-cols-2 lg:grid-rows-2">
            {workflows.map((wf, i) => (
              <AutomationCard key={wf.key} wf={wf} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
