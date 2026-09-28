export type Money = number | string

const API_MONEY_SCALE = 1_000_000

export function parseMoney(value: Money | null | undefined): number | undefined {
  if (value == null || value === "") return undefined
  const n = typeof value === "number" ? value : Number(value)
  return Number.isFinite(n) ? n : undefined
}

/** Convert a presupuesto API amount (millions of ARS) to ARS. */
export function asMoney(value: Money | null | undefined): number | undefined {
  const n = parseMoney(value)
  return n == null ? undefined : n * API_MONEY_SCALE
}

/**
 * Formatea un monto del API (millones de ARS) para leerlo en pantalla.
 *
 * Separadores es-AR — `$7.531,91B`, no `$7531.91B`: la narrativa del producto y
 * la prueba manual comparan contra el ancla con coma decimal y punto de miles.
 * El sufijo sigue siendo la escala corta (B = 10⁹ ARS = mil millones), que es la
 * convención que ya usaba la página de ejecución.
 */
export function formatARS(value: Money | null | undefined): string {
  const n = asMoney(value)
  if (n == null) return "—"
  if (n >= 1e9)
    return `$${(n / 1e9).toLocaleString("es-AR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}B`
  if (n >= 1e6)
    return `$${(n / 1e6).toLocaleString("es-AR", {
      maximumFractionDigits: 0,
    })}M`
  return `$${n.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
}

export function formatPct(pct: number | null | undefined): string {
  if (pct == null) return "—"
  return `${pct.toFixed(1)}%`
}

export function barWidth(pct: number | null | undefined): number {
  if (pct == null || Number.isNaN(pct)) return 0
  return Math.min(Math.max(pct, 0), 100)
}
