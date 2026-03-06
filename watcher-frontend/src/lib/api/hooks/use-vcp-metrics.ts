import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../client";
import type { VCPMetrics } from "../../../types/verification";

export function useVCPMetrics(options?: { refetchInterval?: number }) {
  return useQuery<VCPMetrics>({
    queryKey: ["vcp-metrics"],
    queryFn: async () => {
      const { data } = await apiClient.get("/observability/vcp");
      return data;
    },
    refetchInterval: options?.refetchInterval ?? 30_000,
    staleTime: 15_000,
  });
}

export function useVCPMetricsByBoletin(boletinId: number | undefined) {
  return useQuery<VCPMetrics>({
    queryKey: ["vcp-metrics", boletinId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/observability/vcp/${boletinId}`);
      return data;
    },
    enabled: boletinId != null,
    staleTime: 30_000,
  });
}
