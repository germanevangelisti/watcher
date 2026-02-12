import { useQuery, useMutation } from "@tanstack/react-query"
import apiClient from "../client"

interface Agent {
  agent_type: string
  status: string
  is_available: boolean
  tasks_processed: number
}

interface AgentHealth {
  system_status: string
  agents: Agent[]
  active_workflows: number
  total_tasks_completed: number
}

export function useAgentHealth() {
  return useQuery({
    queryKey: ["agent-health"],
    queryFn: async () => {
      const { data } = await apiClient.get<AgentHealth>("/agents/health")
      return data
    },
    refetchInterval: 10000, // Refetch every 10 seconds
  })
}

interface ChatResponse {
  response: string
  agent?: string
  timestamp?: string
}

export function useAgentChat() {
  return useMutation({
    mutationFn: async (query: string) => {
      const { data } = await apiClient.post<ChatResponse>("/agents/chat", { query })
      return data
    },
  })
}

export function useSystemStatistics() {
  return useQuery({
    queryKey: ["system-statistics"],
    queryFn: async () => {
      const { data } = await apiClient.get("/agents/insights/statistics")
      return data
    },
  })
}

export function useTopRiskDocuments(limit: number = 10) {
  return useQuery({
    queryKey: ["top-risk-documents", limit],
    queryFn: async () => {
      const { data } = await apiClient.get(`/agents/insights/top-risk?limit=${limit}`)
      return data
    },
  })
}

export function useTransparencyTrends(startYear: number = 2025, startMonth: number = 1) {
  return useQuery({
    queryKey: ["transparency-trends", startYear, startMonth],
    queryFn: async () => {
      const { data } = await apiClient.get(
        `/agents/insights/trends?start_year=${startYear}&start_month=${startMonth}`
      )
      return data
    },
  })
}
