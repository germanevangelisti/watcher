import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"

export type JurisdictionLevel = "nacion" | "provincia" | "municipio"

export interface JurisdictionSummary {
  /** Clave en required_documents.json (nacion, cordoba_provincia, cordoba_ciudad) */
  jurisdiction_key?: string
  /** Código real: AR, AR-X, AR-X-CBA */
  jurisdiction_code: string
  jurisdiction_level?: JurisdictionLevel | null
  jurisdiction_id: number | null
  jurisdiction_name: string
  applicable_laws: string[]
  total_documents: number
  missing: number
  downloaded: number
  processed: number
  coverage_percentage: number
  by_type: Record<string, Record<string, number>>
}

export interface TransparencyOverview {
  jurisdictions: JurisdictionSummary[]
  total_documents: number
  total_missing: number
  total_processed: number
  overall_coverage: number
}

export function useTransparencyOverview() {
  return useQuery({
    queryKey: ["transparency-overview"],
    queryFn: async () => {
      const { data } = await apiClient.get<TransparencyOverview>(
        "/compliance/documents/overview"
      )
      return data
    },
    staleTime: 2 * 60 * 1000, // 2 minutes cache
    retry: 1,
  })
}
