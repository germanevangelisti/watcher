import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"
import type { FinalidadesResumen } from "@/types/presupuesto"

/**
 * Techo de la Ley/Mapas agrupado por finalidad (Must de Ampliación B).
 *
 * Sin `scale`: este endpoint no acepta el parámetro y el serializer del backend
 * ya emite millones de ARS siempre. Mandarlo sugeriría una escala elegible que no
 * existe, y el día que alguien la cambiara el frontend multiplicaría dos veces.
 *
 * Un ejercicio sin Ley cargada es un 404 con `detail` explicando que es un hueco
 * y no un techo $0 — la UI lo distingue por el status, no por los ceros.
 */
export function useFinalidades(params?: { ejercicio?: number }) {
  const ejercicio = params?.ejercicio ?? 2026
  return useQuery({
    queryKey: ["presupuesto-finalidades", { ejercicio }],
    staleTime: 0,
    queryFn: async () => {
      const queryParams = new URLSearchParams()
      queryParams.append("ejercicio", ejercicio.toString())
      const { data } = await apiClient.get<FinalidadesResumen>(
        `/presupuesto/finalidades/?${queryParams.toString()}`,
        { headers: { "Cache-Control": "no-store" } }
      )
      if (typeof data === "string") {
        throw new Error("Respuesta inválida del API de finalidades")
      }
      return data
    },
  })
}
