import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"
import type {
  EjecucionFilters,
  EjecucionListResponse,
  EjecucionResumenResponse,
} from "@/types/presupuesto"

export function useEjecucionResumen(params?: { fecha_desde?: string; fecha_hasta?: string }) {
  return useQuery({
    queryKey: ["ejecucion-resumen", params],
    staleTime: 0, // always refetch on mount — resumen is cheap and must reflect latest data
    queryFn: async () => {
      const queryParams = new URLSearchParams()
      if (params?.fecha_desde) queryParams.append("fecha_desde", params.fecha_desde)
      if (params?.fecha_hasta) queryParams.append("fecha_hasta", params.fecha_hasta)
      const { data } = await apiClient.get<EjecucionResumenResponse>(
        `/presupuesto/ejecucion/resumen/?${queryParams.toString()}`
      )
      return data
    },
  })
}

export function useEjecucion(params?: EjecucionFilters) {
  return useQuery({
    queryKey: ["ejecucion", params],
    queryFn: async () => {
      const queryParams = new URLSearchParams()
      if (params?.skip !== undefined) queryParams.append("skip", params.skip.toString())
      if (params?.limit !== undefined) queryParams.append("limit", params.limit.toString())
      if (params?.fecha_desde) queryParams.append("fecha_desde", params.fecha_desde)
      if (params?.fecha_hasta) queryParams.append("fecha_hasta", params.fecha_hasta)
      if (params?.organismo) queryParams.append("organismo", params.organismo)
      if (params?.riesgo) queryParams.append("riesgo", params.riesgo)
      if (params?.solo_canonicos !== undefined)
        queryParams.append("solo_canonicos", params.solo_canonicos.toString())
      if (params?.presupuesto_base_id !== undefined)
        queryParams.append("presupuesto_base_id", params.presupuesto_base_id.toString())
      if (params?.requiere_revision !== undefined)
        queryParams.append("requiere_revision", params.requiere_revision.toString())
      const { data } = await apiClient.get<EjecucionListResponse>(
        `/presupuesto/ejecucion/?${queryParams.toString()}`
      )
      return data
    },
  })
}
