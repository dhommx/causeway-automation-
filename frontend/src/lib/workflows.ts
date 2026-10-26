import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "./api";

export function useDepartments() {
  return useQuery({
    queryKey: ["departments"],
    queryFn: async () => unwrap(await api.GET("/api/v1/departments")),
  });
}

export function useWorkflow(key: string) {
  return useQuery({
    queryKey: ["workflow", key],
    queryFn: async () => unwrap(await api.GET("/api/v1/workflows/{key}", { params: { path: { key } } })),
  });
}
