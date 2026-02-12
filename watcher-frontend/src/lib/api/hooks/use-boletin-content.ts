import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"

// What the backend actually returns
interface BoletinContentBackend {
  content: string
  filename: string
  size_bytes: number
}

// Normalized for frontend
export interface BoletinContent {
  text: string
  filename: string
  total_chars: number
}

export function useBoletinContent(filename?: string) {
  return useQuery({
    queryKey: ["boletin-content", filename],
    queryFn: async () => {
      if (!filename) throw new Error("Filename is required")
      
      const { data } = await apiClient.get<BoletinContentBackend>(
        `/documentos/text/${encodeURIComponent(filename)}`
      )
      // Map backend fields to frontend fields
      return {
        text: data.content,
        filename: data.filename,
        total_chars: data.content?.length ?? 0,
      } as BoletinContent
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
