import { describe, it, expect } from "vitest"
import { barWidth, formatARS, formatPct } from "@/lib/presupuesto-format"

describe("formatARS", () => {
  it("formats billions from API millions", () => {
    expect(formatARS(2_627_774.687)).toBe("$2627.8B")
  })

  it("formats millions from API millions", () => {
    expect(formatARS(500)).toBe("$500M")
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
