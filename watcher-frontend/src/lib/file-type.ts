/**
 * Eje de tipos de archivo del inventario de transparencia.
 *
 * Decisión PO (2026-09-28): "Documentos por tipo" se muestra por **tipo de archivo**
 * (primario) con la categoría legal como detalle (secundario). Las etiquetas y el
 * orden los publica el backend en `file_type_taxonomy`, así que acá no se adivina el
 * nombre de un formato: si la taxonomía todavía no llegó (backend anterior a 1.1.0),
 * se cae al eje legal `by_type` — el contrato viejo no se rompe en silencio.
 */

export interface FileTypeBucket {
  total: number
  missing: number
  downloaded: number
  processed: number
  /** Mapping al eje legal: cuántos documentos de este tipo son de cada categoría. */
  legal_categories: Record<string, number>
}

export interface FileTypeInfo {
  key: string
  label: string
}

export interface FileTypeRow {
  key: string
  label: string
  total: number
  available: number
  /** Detalle secundario: categorías legales dentro del tipo de archivo. */
  legalCategories: { key: string; label: string; count: number }[]
}

export function legalCategoryLabel(category: string): string {
  return category.replace(/_/g, " ")
}

/** Etiqueta del tipo de archivo, tomada de la taxonomía publicada por el backend. */
export function fileTypeLabel(key: string, taxonomy?: FileTypeInfo[] | null): string {
  return taxonomy?.find((entry) => entry.key === key)?.label ?? key.toUpperCase()
}

function taxonomyOrder(key: string, taxonomy?: FileTypeInfo[] | null): number {
  const index = taxonomy?.findIndex((entry) => entry.key === key) ?? -1
  return index === -1 ? Number.MAX_SAFE_INTEGER : index
}

function availableOf(counts: { downloaded?: number; processed?: number }): number {
  return (counts.downloaded ?? 0) + (counts.processed ?? 0)
}

/** Filas del eje primario (tipo de archivo), con el mapping legal como detalle. */
export function fileTypeRows(
  byFileType: Record<string, FileTypeBucket> | undefined,
  taxonomy?: FileTypeInfo[] | null
): FileTypeRow[] {
  return Object.entries(byFileType ?? {})
    .map(([key, bucket]) => {
      const legalCategories = Object.entries(bucket.legal_categories ?? {})
        .map(([legalKey, count]) => ({ key: legalKey, label: legalCategoryLabel(legalKey), count }))
        .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))

      return {
        key,
        label: fileTypeLabel(key, taxonomy),
        // Un documento cae en un solo bucket: si `total` faltara, la suma del
        // mapping legal es la misma cuenta.
        total: bucket.total ?? legalCategories.reduce((sum, c) => sum + c.count, 0),
        available: availableOf(bucket),
        legalCategories,
      }
    })
    .sort(
      (a, b) =>
        taxonomyOrder(a.key, taxonomy) - taxonomyOrder(b.key, taxonomy) ||
        a.label.localeCompare(b.label)
    )
}

/** Fallback al eje legal cuando el backend todavía no publica `by_file_type`. */
export function legalTypeRows(
  byType:
    | Record<string, { total?: number; missing?: number; downloaded?: number; processed?: number }>
    | undefined
): FileTypeRow[] {
  return Object.entries(byType ?? {}).map(([key, counts]) => ({
    key,
    label: legalCategoryLabel(key),
    total: counts.total ?? (counts.missing ?? 0) + availableOf(counts),
    available: availableOf(counts),
    legalCategories: [],
  }))
}
