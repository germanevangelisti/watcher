import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"
import type { Boletin, BoletinBackend, BoletinesFilters } from "@/types"

// Helper to parse date "YYYYMMDD" to year/month
function parseDateString(dateStr: string): { year: number; month: number } {
  const year = parseInt(dateStr.substring(0, 4))
  const month = parseInt(dateStr.substring(4, 6))
  return { year, month }
}

// Transform backend response to frontend structure
function transformBoletin(backend: BoletinBackend): Boletin {
  const { year, month } = parseDateString(backend.date)
  
  return {
    id: backend.id,
    filename: backend.filename,
    date: backend.date,
    year,
    month,
    section: backend.section,
    processed: backend.status === "completed",
    created_at: backend.created_at,
    updated_at: backend.updated_at,
    status: backend.status,
    fuente: backend.fuente,
    jurisdiccion_nombre: backend.jurisdiccion_nombre,
    seccion_nombre: backend.seccion_nombre,
  }
}

export function useBoletines(filters?: BoletinesFilters) {
  return useQuery({
    queryKey: ["boletines", filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      
      if (filters?.skip !== undefined) params.append("skip", filters.skip.toString())
      if (filters?.limit) params.append("limit", filters.limit.toString())
      if (filters?.year) params.append("year", filters.year.toString())
      if (filters?.month) params.append("month", filters.month.toString())
      if (filters?.section) params.append("section", filters.section)
      if (filters?.processed !== undefined) {
        // Backend uses "status" field with values "completed" or "pending"
        params.append("status", filters.processed ? "completed" : "pending")
      }

      const { data } = await apiClient.get<BoletinBackend[]>(
        `/boletines/?${params.toString()}`
      )

      // Backend returns a direct array, not a paginated object
      const boletines = (data || []).map(transformBoletin)
      
      return {
        boletines,
        total: boletines.length,  // Backend returns filtered results, not total count
        page: Math.floor((filters?.skip || 0) / (filters?.limit || 12)) + 1,
        page_size: filters?.limit || 12,
      }
    },
  })
}

export function useBoletin(id: number) {
  return useQuery({
    queryKey: ["boletin", id],
    queryFn: async () => {
      const { data } = await apiClient.get<BoletinBackend>(`/boletines/${id}`)
      return transformBoletin(data)
    },
    enabled: !!id,
  })
}
