import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"
import type {
  EjecucionFilters,
  EjecucionListResponse,
  EjecucionResumenResponse,
  JurisdiccionGasto,
} from "@/types/presupuesto"

export function useEjecucionResumen(params?: {
  fecha_desde?: string
  fecha_hasta?: string
  jurisdiccion?: JurisdiccionGasto
}) {
  return useQuery({
    queryKey: ["ejecucion-resumen", params],
    staleTime: 0,
    queryFn: async () => {
      const queryParams = new URLSearchParams()
      if (params?.fecha_desde) queryParams.append("fecha_desde", params.fecha_desde)
      if (params?.fecha_hasta) queryParams.append("fecha_hasta", params.fecha_hasta)
      if (params?.jurisdiccion) queryParams.append("jurisdiccion", params.jurisdiccion)
      queryParams.append("scale", "millions")
      const { data } = await apiClient.get<EjecucionResumenResponse>(
        `/presupuesto/ejecucion/resumen/?${queryParams.toString()}`,
        { headers: { "Cache-Control": "no-store" } }
      )
      if (typeof data === "string") {
        throw new Error("Respuesta inválida del API de ejecución")
      }
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
      if (params?.jurisdiccion) queryParams.append("jurisdiccion", params.jurisdiccion)
      if (params?.etapa_gasto) queryParams.append("etapa_gasto", params.etapa_gasto)
      queryParams.append("scale", "millions")
      const { data } = await apiClient.get<EjecucionListResponse>(
        `/presupuesto/ejecucion/?${queryParams.toString()}`,
        { headers: { "Cache-Control": "no-store" } }
      )
      if (typeof data === "string") {
        throw new Error("Respuesta inválida del API de ejecución")
      }
      return data
    },
  })
}
