import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"

export interface DashboardStats {
  total_documents: number
  total_chunks: number
  total_entities: number
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: async () => {
      const { data } = await apiClient.get<DashboardStats>("/dashboard/stats")
      return data
    },
  })
}
