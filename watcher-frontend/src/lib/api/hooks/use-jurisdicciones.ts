import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"
import type { JurisdiccionSimple } from "@/types"

export function useJurisdicciones() {
  return useQuery({
    queryKey: ["jurisdicciones"],
    queryFn: async () => {
      const { data } = await apiClient.get<JurisdiccionSimple[]>("/jurisdicciones/", {
        params: { limit: 500 },
      })
      return data
    },
    staleTime: 5 * 60 * 1000, // 5 minutes cache
  })
}
