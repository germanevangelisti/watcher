/**
 * Pipeline REST hooks - TanStack Query hooks for pipeline API endpoints.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiClient } from "../client"
import type { PipelineConfigState } from "@/lib/store/pipeline-store"

// =============================================================================
// Types
// =============================================================================

export interface PipelineStatusResponse {
  total_boletines: number
  by_status: Record<string, number>
  total_chunks: number
  total_indexed: number
  active_session: {
    session_id: string
    total: number
    current: number
    status: string
    config: PipelineConfigState
    errors: Array<{ boletin_id: number; filename: string; error: string }>
  } | null
}

export interface ResetResponse {
  success: boolean
  message?: string
  chunks_deleted: number
  chromadb_cleared: boolean
  txt_files_deleted: number
  boletines_reset: number
}

export interface ResetDocumentResponse {
  success: boolean
  boletin_id: number
  filename: string
  chunks_deleted: number
  chromadb_deleted: number
  txt_deleted: boolean
  previous_status: string
}

export interface ProcessResponse {
  success: boolean
  session_id: string
  boletin_id?: number
  filename?: string
  total?: number
  message: string
  config: PipelineConfigState
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Get pipeline status (auto-refetch every 5 seconds)
 */
export function usePipelineStatus(enabled = true) {
  return useQuery({
    queryKey: ["pipeline", "status"],
    queryFn: async () => {
      const { data } = await apiClient.get<PipelineStatusResponse>("/pipeline/status")
      return data
    },
    refetchInterval: enabled ? 5000 : false,
    staleTime: 3000,
  })
}

/**
 * Get default pipeline configuration
 */
export function usePipelineDefaults() {
  return useQuery({
    queryKey: ["pipeline", "config", "defaults"],
    queryFn: async () => {
      const { data } = await apiClient.get<PipelineConfigState>("/pipeline/config/defaults")
      return data
    },
    staleTime: 60000, // defaults rarely change
  })
}

/**
 * Reset ALL pipeline data (requires double confirmation)
 */
export function usePipelineResetAll() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post<ResetResponse>("/pipeline/reset", null, {
        headers: {
          "X-Confirm-Reset": "RESET_ALL_DATA",
        },
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline"] })
      queryClient.invalidateQueries({ queryKey: ["boletines"] })
      queryClient.invalidateQueries({ queryKey: ["dashboard"] })
    },
  })
}

/**
 * Reset a single document's pipeline data
 */
export function usePipelineResetOne() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (boletinId: number) => {
      const { data } = await apiClient.post<ResetDocumentResponse>(
        `/pipeline/reset/${boletinId}`
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline"] })
      queryClient.invalidateQueries({ queryKey: ["boletines"] })
    },
  })
}

/**
 * Process a single document through the pipeline
 */
export function usePipelineProcessOne() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      boletinId,
      config,
    }: {
      boletinId: number
      config?: PipelineConfigState
    }) => {
      const { data } = await apiClient.post<ProcessResponse>(
        `/pipeline/process/${boletinId}`,
        config || null
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline"] })
      queryClient.invalidateQueries({ queryKey: ["boletines"] })
    },
  })
}

/**
 * Process all pending documents through the pipeline
 */
export function usePipelineProcessAll() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (config?: PipelineConfigState) => {
      const { data } = await apiClient.post<ProcessResponse>(
        "/pipeline/process-all",
        config || null
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipeline"] })
      queryClient.invalidateQueries({ queryKey: ["boletines"] })
    },
  })
}
