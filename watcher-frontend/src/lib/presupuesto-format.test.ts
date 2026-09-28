import { describe, it, expect } from "vitest"
import { barWidth, formatARS, formatPct } from "@/lib/presupuesto-format"

describe("formatARS", () => {
  it("formats billions from API millions, with es-AR separators", () => {
    // Coma decimal y punto de miles: es lo que lee la narrativa del producto.
    expect(formatARS(2_627_774.687)).toBe("$2.627,77B")
  })

  it("formats millions from API millions", () => {
    expect(formatARS(500)).toBe("$500M")
  })

  it("renders the corte anchor the manual test compares against", () => {
    // 7.531.910 millones de ARS = $7.531,91B: el techo 2026 completo.
    expect(formatARS(7_531_910)).toBe("$7.531,91B")
  })

  it("groups the thousands of sub-million amounts", () => {
    // 0.5 millones de ARS = 500.000 ARS, con punto de miles es-AR.
    expect(formatARS(0.5)).toBe("$500.000")
  })

  it("returns em dash for null", () => {
    expect(formatARS(null)).toBe("—")
  })
})

describe("formatPct", () => {
  it("formats one decimal", () => {
    expect(formatPct(2.87)).toBe("2.9%")
  })

  it("returns em dash without denominator", () => {
    expect(formatPct(null)).toBe("—")
  })
})

describe("barWidth", () => {
  it("caps over-commitment at 100 for the fill", () => {
    expect(barWidth(295.41)).toBe(100)
  })

  it("keeps values under 100", () => {
    expect(barWidth(86.55)).toBe(86.55)
  })

  it("is zero without a percentage", () => {
    expect(barWidth(null)).toBe(0)
  })
})
