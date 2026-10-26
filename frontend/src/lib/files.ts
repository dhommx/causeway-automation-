import { useMutation, useQuery } from "@tanstack/react-query";

import { errorMessage, type Preview, type StoredFile } from "./api";

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
