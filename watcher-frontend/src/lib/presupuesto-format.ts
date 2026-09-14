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

export function formatARS(value: Money | null | undefined): string {
  const n = asMoney(value)
  if (n == null) return "—"
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`
  if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`
  return `$${n.toLocaleString("es-AR")}`
}

export function formatPct(pct: number | null | undefined): string {
  if (pct == null) return "—"
  return `${pct.toFixed(1)}%`
}

export function barWidth(pct: number | null | undefined): number {
  if (pct == null || Number.isNaN(pct)) return 0
  return Math.min(Math.max(pct, 0), 100)
}
