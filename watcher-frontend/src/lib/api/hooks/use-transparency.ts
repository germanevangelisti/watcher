import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"
import type { ApplicableLaw } from "@/lib/applicable-law"
import type { FileTypeBucket, FileTypeInfo } from "@/lib/file-type"

export type { ApplicableLaw }
export type { FileTypeBucket, FileTypeInfo }

export type JurisdictionLevel = "nacion" | "provincia" | "municipio"

export interface JurisdictionSummary {
  /** Clave en required_documents.json (nacion, cordoba_provincia, cordoba_ciudad) */
  jurisdiction_key?: string
  /** Código real: AR, AR-X, AR-X-CBA */
  jurisdiction_code: string
  jurisdiction_level?: JurisdictionLevel | null
  jurisdiction_id: number | null
  jurisdiction_name: string
  applicable_laws: ApplicableLaw[]
  total_documents: number
  missing: number
  downloaded: number
  processed: number
  coverage_percentage: number
  /** Eje legal (contrato original): fallback si el backend no publica `by_file_type`. */
  by_type: Record<string, Record<string, number>>
  /** Eje primario de presentación (contrato 1.1.0): tipo de archivo + mapping legal. */
  by_file_type?: Record<string, FileTypeBucket>
}

export interface TransparencyOverview {
  jurisdictions: JurisdictionSummary[]
  total_documents: number
  total_missing: number
  total_processed: number
  overall_coverage: number
  /** Taxonomía de tipos de archivo, en orden de presentación. */
  file_type_taxonomy?: FileTypeInfo[]
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
