import { useMutation } from "@tanstack/react-query"
import apiClient from "../client"
import type { SearchRequest, SearchResponse } from "@/types"

export function useSearch() {
  return useMutation({
    mutationFn: async (request: SearchRequest) => {
      const { data } = await apiClient.post<SearchResponse>("/search/", request)
      return data
    },
  })
}
