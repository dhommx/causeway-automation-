import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap, type Run } from "./api";

const FINISHED = new Set(["succeeded", "failed"]);
export const isFinished = (run?: Run) => !!run && FINISHED.has(run.status);

export type RunRequest = {
  workflow_key: string;
  inputs: Record<string, { id: string; password?: string | null }[]>;
  params: Record<string, unknown>;
};

export function useCreateRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: RunRequest) => unwrap(await api.POST("/api/v1/runs", { body })),
    onSuccess: (run) => qc.invalidateQueries({ queryKey: ["runs", run.workflow_key] }),
  });
}

/** One run, polled every second until it finishes. */
export function useRun(runId: string | null) {
  const qc = useQueryClient();
  return useQuery({
    queryKey: ["run", runId],
    enabled: !!runId,
    queryFn: async () => {
      const run = unwrap(await api.GET("/api/v1/runs/{run_id}", { params: { path: { run_id: runId! } } }));
      if (isFinished(run)) qc.invalidateQueries({ queryKey: ["runs", run.workflow_key] });
      return run;
    },
    refetchInterval: (q) => (isFinished(q.state.data) ? false : 1000),
  });
}

export function useRuns(workflowKey: string) {
  return useQuery({
    queryKey: ["runs", workflowKey],
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/runs", { params: { query: { workflow_key: workflowKey, limit: 200 } } })),
  });
}

export function useRunAudit(runId: string | null) {
  return useQuery({
    queryKey: ["audit", runId],
    enabled: !!runId,
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/audit", { params: { query: { entity_type: "run", entity_id: runId! } } })),
  });
}

export function duration(run: Run): string {
  if (!run.started_at || !run.finished_at) return "-";
  const ms = new Date(run.finished_at).getTime() - new Date(run.started_at).getTime();
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
