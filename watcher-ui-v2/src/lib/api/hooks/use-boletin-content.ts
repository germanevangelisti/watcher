import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"

interface BoletinContent {
  text: string
  filename: string
  total_chars: number
}

export function useBoletinContent(filename?: string) {
  return useQuery({
    queryKey: ["boletin-content", filename],
    queryFn: async () => {
      if (!filename) throw new Error("Filename is required")
      
      const { data } = await apiClient.get<BoletinContent>(
        `/documentos/text/${encodeURIComponent(filename)}`
      )
      return data
    },
    enabled: !!filename,
  })
}

export function useBoletinAnalisis(id: number) {
  return useQuery({
    queryKey: ["boletin-analisis", id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/boletines/${id}/analisis`)
      return data
    },
    enabled: !!id,
  })
}
