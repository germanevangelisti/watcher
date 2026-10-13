import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import apiClient from "../client"
import type {
  AnalisisPrecio,
  GastoDetectadoResponse,
  GastoFiltros,
  ObservablesResponse,
} from "@/types/precio-mercado"

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
 * M8 — gasto público detectado en los boletines, con filtros, total y suma.
 * Los filtros y el paginado corren en SQL contra las columnas persistidas, así
 * que vaciar un filtro es una query nueva, no un re-cálculo del corpus.
 */
export function useGastoDetectado(filtros: GastoFiltros = {}) {
  const { limit = 50, offset = 0, ...resto } = filtros
  const qp = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  for (const [clave, valor] of Object.entries(resto)) {
    // `""` significa "sin filtro": mandarlo como query vacía filtría por vacío.
    if (valor !== undefined && valor !== null && valor !== "") qp.append(clave, String(valor))
  }
  const query = qp.toString()
  return useQuery({
    queryKey: ["gasto-detectado", query],
    queryFn: async () => {
      const { data } = await apiClient.get<GastoDetectadoResponse>(`/gasto/detectado?${query}`)
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
