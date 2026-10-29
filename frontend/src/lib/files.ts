import { useMutation, useQueries, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { errorMessage, type Preview, type Schemas, type StoredFile } from "./api";

type CheckRequest = { slot: string; id: string; password: string; params: Record<string, string> };
/** A file's check before Run: still running, or its result. */
export type FileCheckState = { pending: true } | ({ pending: false } & Schemas["FileCheckOut"]);

export function useUploadFiles() {
  return useMutation({
    mutationFn: async (files: File[]): Promise<StoredFile[]> => {
      const body = new FormData();
      files.forEach((f) => body.append("files", f));
      const res = await fetch("/api/v1/files", { method: "POST", body });
      const json = await res.json();
      if (!res.ok) throw new Error(errorMessage(json, "Upload failed."));
      return json;
    },
  });
}

export function usePreview(fileId: string | null, sheet: string | null, password: string | null) {
  return useQuery({
    queryKey: ["preview", fileId, sheet, password],
    enabled: !!fileId,
    retry: false,
    queryFn: async () => {
      const params = new URLSearchParams();
      if (sheet) params.set("sheet", sheet);
      if (password) params.set("password", password);
      const res = await fetch(`/api/v1/files/${fileId}/preview?${params}`);
      const json = await res.json();
      if (!res.ok) throw new Error(errorMessage(json, "Preview failed."));
      return json as Preview;
    },
  });
}

/**
 * The workflow's check on each file of a `checked` slot (e.g. the AFS totals add up), by file id.
 * Waits until typing stops, so a password is not checked on every key press.
 */
export function useFileChecks(workflowKey: string, requests: CheckRequest[]): Map<string, FileCheckState> {
  const wanted = JSON.stringify(requests);
  const [settled, setSettled] = useState(wanted);
  useEffect(() => {
    const t = setTimeout(() => setSettled(wanted), 400);
    return () => clearTimeout(t);
  }, [wanted]);
  const sent = JSON.parse(settled) as CheckRequest[];

  const results = useQueries({
    queries: sent.map((r) => ({
      queryKey: ["file-check", workflowKey, r.slot, r.id, r.password, r.params],
      retry: false,
      staleTime: Infinity,
      queryFn: async (): Promise<Schemas["FileCheckOut"]> => {
        const res = await fetch(`/api/v1/workflows/${workflowKey}/check-file`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slot: r.slot, id: r.id, password: r.password || null, params: r.params }),
        });
        const json = await res.json();
        if (!res.ok) throw new Error(errorMessage(json, "The file could not be checked."));
        return json;
      },
    })),
  });

  const states = new Map<string, FileCheckState>();
  for (const r of requests) {
    const i = sent.findIndex((s) => JSON.stringify(s) === JSON.stringify(r));
    const q = i >= 0 ? results[i] : undefined;
    if (!q || q.isPending) states.set(r.id, { pending: true });
    else if (q.error) states.set(r.id, { pending: false, ok: false, message: q.error.message });
    else states.set(r.id, { pending: false, ...q.data! });
  }
  return states;
}

/** True when a typed amount still equals the value a file check filled in ("22" equals "22.000"). */
export function sameValue(typed: string | undefined, filled: string): boolean {
  const a = (typed ?? "").trim();
  return a === filled || (a !== "" && Number(a) === Number(filled));
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

/** "3 files added" + "2 XLSX, 1 CSV", for the upload notice. */
export function describeUpload(files: StoredFile[]): { title: string; detail: string } {
  const counts = new Map<string, number>();
  for (const f of files) {
    const ext = f.original_name.includes(".") ? f.original_name.split(".").pop()!.toUpperCase() : "Unknown";
    counts.set(ext, (counts.get(ext) ?? 0) + 1);
  }
  const n = files.length;
  return {
    title: `${n} ${n === 1 ? "file" : "files"} added`,
    detail: [...counts].map(([ext, c]) => `${c} ${ext}`).join(", "),
  };
}
