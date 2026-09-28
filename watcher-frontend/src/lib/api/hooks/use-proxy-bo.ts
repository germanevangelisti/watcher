import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"
import type { ProxyBoResumen } from "@/types/presupuesto"

/**
 * Proxy BO por finalidad (Should de Ampliación B): lo **publicado** en el Boletín
 * Oficial atribuido a cada finalidad, contra el techo de esa finalidad.
 *
 * No es ejecución. El numerador es llamado + adjudicación + contrato + pago, y la
 * respuesta trae `honestidad.es_devengado: false` junto con la etiqueta que hay que
 * mostrar. Este hook no la reinterpreta: el componente lee `etiqueta_numerador`.
 *
 * Mismas reglas que `useFinalidades`: sin `scale`, `staleTime: 0`, guard contra la
 * respuesta que llega como string, y el 404 se propaga como error (es el hueco:
 * sin Ley cargada no hay contra qué contrastar).
 */
export function useProxyBo(params?: { ejercicio?: number }) {
  const ejercicio = params?.ejercicio ?? 2026
  return useQuery({
    queryKey: ["presupuesto-proxy-bo", { ejercicio }],
    staleTime: 0,
    queryFn: async () => {
      const queryParams = new URLSearchParams()
      queryParams.append("ejercicio", ejercicio.toString())
      const { data } = await apiClient.get<ProxyBoResumen>(
        `/presupuesto/finalidades/proxy-bo/?${queryParams.toString()}`,
        { headers: { "Cache-Control": "no-store" } }
      )
      if (typeof data === "string") {
        throw new Error("Respuesta inválida del API del proxy BO")
      }
      return data
    },
  })
}
