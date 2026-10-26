import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "./api";

export function useRules(key: string) {
  return useQuery({
    queryKey: ["rules", key],
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/workflows/{key}/rules", { params: { path: { key } } })),
  });
}

export function useSaveRules(key: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { values: Record<string, unknown>; note: string }) =>
      unwrap(await api.PUT("/api/v1/workflows/{key}/rules", { params: { path: { key } }, body })),
    onSuccess: (data) => qc.setQueryData(["rules", key], data),
  });
}
