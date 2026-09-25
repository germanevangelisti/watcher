import { useMutation, useQueryClient } from "@tanstack/react-query"
import apiClient from "../client"

/** Un archivo dentro de la respuesta de `POST /upload/files`. */
export interface UploadResultItem {
  filename: string | null
  status: "uploaded" | "duplicate" | "failed"
  boletin_id?: number
  file_hash?: string
  file_size_bytes?: number
  duplicate_of?: string
  error?: string
}

export interface BatchUploadResponse {
  total: number
  uploaded: number
  duplicates: number
  failed: number
  results: UploadResultItem[]
}

/**
 * Sube PDFs al backend (`POST /upload/files`).
 *
 * El endpoint espera el campo **`files`** (una lista, hasta 50 por request), no
 * `file`.  Mandar los N archivos en un solo request es, además, lo que el
 * endpoint fue escrito para hacer: deduplica por SHA256 dentro del lote.
 *
 * No seteamos `Content-Type` a mano: axios lo arma con el `boundary` correcto
 * cuando el body es un `FormData`.
 */
export function useUploadFiles() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (files: File[]) => {
      const formData = new FormData()
      for (const file of files) formData.append("files", file)
      const { data } = await apiClient.post<BatchUploadResponse>("/upload/files", formData)
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["boletines"] })
      qc.invalidateQueries({ queryKey: ["boletin-calendar"] })
    },
  })
}
