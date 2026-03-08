import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"
import type { CalendarResponse } from "@/types"

export function useBoletinCalendar(
  year: number,
  month: number,
  jurisdiccionId?: number,
) {
  return useQuery({
    queryKey: ["boletin-calendar", year, month, jurisdiccionId],
    queryFn: async () => {
      const params = new URLSearchParams({
        year: year.toString(),
        month: month.toString(),
      })
      if (jurisdiccionId !== undefined) {
        params.append("jurisdiccion_id", jurisdiccionId.toString())
      }
      const { data } = await apiClient.get<CalendarResponse>(
        `/boletines/calendar?${params.toString()}`
      )
      return data
    },
    staleTime: 10_000,
    // Refresca cada 12 s mientras haya secciones procesando; cae a 60 s en reposo
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) return 12_000
      const hasProcessing = data.jurisdicciones.some((j) =>
        Object.values(j.dias).some((d) =>
          d.secciones.some((s) => s.status === "processing")
        )
      )
      return hasProcessing ? 8_000 : 60_000
    },
  })
}
