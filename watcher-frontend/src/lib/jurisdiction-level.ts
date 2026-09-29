import type { JurisdictionLevel, JurisdictionSummary } from "@/lib/api/hooks/use-transparency"

const LEVELS: readonly JurisdictionLevel[] = ["nacion", "provincia", "municipio"]

export const JURISDICTION_LEVEL_LABEL: Record<JurisdictionLevel, string> = {
  nacion: "Nación",
  provincia: "Provincia",
  municipio: "Ciudad / Municipio",
}

/**
 * Nivel de una jurisdicción del overview de compliance.
 *
 * Usa `jurisdiction_level` del API; si falta (API vieja), lo deduce del código
 * real (`AR` → nación, `AR-X` → provincia, `AR-X-CBA` → municipio) o de la
 * clave de config (`nacion`, `cordoba_provincia`, ...).
 */
export function getJurisdictionLevel(
  j: Pick<JurisdictionSummary, "jurisdiction_code" | "jurisdiction_level" | "jurisdiction_key">
): JurisdictionLevel {
  if (j.jurisdiction_level && LEVELS.includes(j.jurisdiction_level)) return j.jurisdiction_level

  const code = (j.jurisdiction_code || "").toUpperCase()
  if (code === "AR" || code === "NACION") return "nacion"
  if (/^AR-[A-Z]$/.test(code)) return "provincia"

  const key = (j.jurisdiction_key || j.jurisdiction_code || "").toLowerCase()
  if (key === "nacion") return "nacion"
  if (key.endsWith("_provincia")) return "provincia"
  return "municipio"
}
