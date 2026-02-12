import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import apiClient from "../client"
import type { 
  Alerta, 
  AlertasListResponse, 
  AlertasStats, 
  AlertaUpdate,
  AlertasFilters 
} from "@/types/alertas"

interface UseAlertasParams extends AlertasFilters {
  skip?: number
  limit?: number
}

export function useAlertas(params?: UseAlertasParams) {
  return useQuery({
    queryKey: ["alertas", params],
    queryFn: async () => {
      const queryParams = new URLSearchParams()
      
      if (params?.skip !== undefined) queryParams.append("skip", params.skip.toString())
      if (params?.limit !== undefined) queryParams.append("limit", params.limit.toString())
      if (params?.nivel_severidad) queryParams.append("nivel_severidad", params.nivel_severidad)
      if (params?.tipo_alerta) queryParams.append("tipo_alerta", params.tipo_alerta)
      if (params?.organismo) queryParams.append("organismo", params.organismo)
      if (params?.estado) queryParams.append("estado", params.estado)
      
      const { data } = await apiClient.get<AlertasListResponse>(
        `/alertas/?${queryParams.toString()}`
      )
      return data
    },
  })
}

export function useAlerta(alertaId?: number) {
  return useQuery({
    queryKey: ["alerta", alertaId],
    queryFn: async () => {
      if (!alertaId) throw new Error("Alerta ID is required")
      const { data } = await apiClient.get<Alerta>(`/alertas/${alertaId}`)
      return data
    },
    enabled: !!alertaId,
  })
}

export function useAlertasStats() {
  return useQuery({
    queryKey: ["alertas-stats"],
    queryFn: async () => {
      const { data } = await apiClient.get<AlertasStats>("/alertas/stats/")
      return data
    },
  })
}

export function useUpdateAlerta() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ alertaId, update }: { alertaId: number; update: AlertaUpdate }) => {
      const { data } = await apiClient.patch<Alerta>(
        `/alertas/${alertaId}/estado`,
        update
      )
      return data
    },
    onSuccess: (data) => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ["alertas"] })
      queryClient.invalidateQueries({ queryKey: ["alerta", data.id] })
      queryClient.invalidateQueries({ queryKey: ["alertas-stats"] })
    },
  })
}
