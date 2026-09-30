/**
 * Ley aplicable a una jurisdicción (contrato overview `1.1.0`).
 *
 * `official_url` es `null`/ausente cuando no hay fuente oficial verificable: la UI
 * muestra el nombre + "sin URL" y **no** inventa un link (decisión PO 2026-09-28).
 */
export interface ApplicableLaw {
  name: string
  official_url?: string | null
}

/**
 * Normaliza el contrato viejo (`applicable_laws: string[]`) sin romper la vista:
 * un string suelto no trae URL, así que se lee como "sin URL".
 */
export function toApplicableLaw(law: ApplicableLaw | string): ApplicableLaw {
  return typeof law === "string" ? { name: law, official_url: null } : law
}
