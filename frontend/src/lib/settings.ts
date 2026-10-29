import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "./api";

export function useSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: async () => unwrap(await api.GET("/api/v1/settings")),
  });
}

/** data_folder: null goes back to the default folder. */
export function useSaveSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { data_folder: string | null }) =>
      unwrap(await api.PUT("/api/v1/settings", { body })),
    onSuccess: (data) => qc.setQueryData(["settings"], data),
  });
}
