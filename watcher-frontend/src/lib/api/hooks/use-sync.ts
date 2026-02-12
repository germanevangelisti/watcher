import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import apiClient from "../client"

export interface JurisdiccionSyncConfig {
  id: number
  jurisdiccion_id: number
  jurisdiccion_nombre: string | null
  source_url_template: string | null
  scraper_type: string
  sync_enabled: boolean
  sync_frequency: string
  last_sync_date: string | null
  last_sync_status: string
  last_sync_error: string | null
  sections_to_sync: string[] | null
  extra_config: Record<string, unknown> | null
}

export function useSyncConfigs() {
  return useQuery({
    queryKey: ["sync-configs"],
    queryFn: async () => {
      const { data } = await apiClient.get<JurisdiccionSyncConfig[]>(
        "/sync/jurisdictions/configs"
      )
      return data
    },
    staleTime: 60 * 1000,
  })
}

export function useTriggerJurisdictionSync() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ jurisdiccionId, processAfterDownload = true }: {
      jurisdiccionId: number
      processAfterDownload?: boolean
    }) => {
      const { data } = await apiClient.post(
        `/sync/jurisdictions/${jurisdiccionId}/trigger?process_after_download=${processAfterDownload}`
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sync-configs"] })
    },
  })
}

export function useUpdateSyncConfig() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ jurisdiccionId, config }: {
      jurisdiccionId: number
      config: {
        source_url_template?: string | null
        scraper_type?: string
        sync_enabled?: boolean
        sync_frequency?: string
        sections_to_sync?: string[] | null
        extra_config?: Record<string, unknown> | null
      }
    }) => {
      const { data } = await apiClient.put(
        `/sync/jurisdictions/${jurisdiccionId}/config`,
        config
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sync-configs"] })
    },
  })
}
