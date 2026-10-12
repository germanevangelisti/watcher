import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import apiClient from "../client"
import type { AnalisisPrecio, ObservablesResponse } from "@/types/precio-mercado"

/** Gastos observables detectados sobre los actos existentes (epic:precio-mercado). */
export function useObservables(params: { q?: string; limit?: number; offset?: number } = {}) {
  const { q = "", limit = 50, offset = 0 } = params
  return useQuery({
    queryKey: ["precio-mercado-observables", { q, limit, offset }],
    queryFn: async () => {
      const qp = new URLSearchParams({ limit: String(limit), offset: String(offset) })
      if (q) qp.append("q", q)
      const { data } = await apiClient.get<ObservablesResponse>(`/precio-mercado/observables?${qp.toString()}`)
      return data
    },
  })
}

/**
 * Análisis a pedido del usuario. Puede tardar (modelo local + fuentes externas),
 * por eso el timeout es más largo que el default del cliente.
 */
export function useAnalizarPrecio() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (ejecucionId: number) => {
      const { data } = await apiClient.post<AnalisisPrecio>(
        `/precio-mercado/analizar/${ejecucionId}`,
        undefined,
        { timeout: 180000 },
      )
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["precio-mercado-observables"] }),
  })
}
