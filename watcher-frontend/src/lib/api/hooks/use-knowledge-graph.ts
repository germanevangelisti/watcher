import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"
import type { GraphData, EntityTimeline } from "@/types"

interface KnowledgeGraphParams {
  max_nodes?: number
  min_mentions?: number
  entity_types?: string[]
}

export function useKnowledgeGraph(params?: KnowledgeGraphParams) {
  return useQuery({
    queryKey: ["knowledge-graph", params],
    queryFn: async () => {
      const queryParams = new URLSearchParams()
      
      if (params?.max_nodes) queryParams.append("max_nodes", params.max_nodes.toString())
      if (params?.min_mentions) queryParams.append("min_mentions", params.min_mentions.toString())
      
      const { data } = await apiClient.get<GraphData>(
        `/entidades/graph?${queryParams.toString()}`
      )
      return data
    },
  })
}

export function useEntityTimeline(entityId?: string | number) {
  return useQuery({
    queryKey: ["entity-timeline", entityId],
    queryFn: async () => {
      if (!entityId) throw new Error("Entity ID is required")
      const { data } = await apiClient.get<EntityTimeline>(`/entidades/${entityId}/timeline`)
      return data
    },
    enabled: !!entityId,
  })
}

export function useEntityStats() {
  return useQuery({
    queryKey: ["entity-stats"],
    queryFn: async () => {
      const { data } = await apiClient.get("/entidades/stats")
      return data
    },
  })
}
