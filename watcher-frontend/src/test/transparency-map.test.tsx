import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, within } from "@testing-library/react"
import { TransparencyMap } from "@/components/features/transparency-map"
import { getJurisdictionLevel } from "@/lib/jurisdiction-level"
import type { TransparencyOverview } from "@/lib/api/hooks/use-transparency"

const hookState: { data?: TransparencyOverview; isLoading: boolean; error: unknown } = {
  isLoading: false,
  error: null,
}

vi.mock("@/lib/api/hooks/use-transparency", () => ({
  useTransparencyOverview: () => hookState,
}))

/** Shape real de GET /compliance/documents/overview tras fix-hierarchy-load (22 docs). */
const OVERVIEW: TransparencyOverview = {
  total_documents: 22,
  total_missing: 19,
  total_processed: 2,
  overall_coverage: 9.09,
  jurisdictions: [
    {
      jurisdiction_key: "cordoba_ciudad",
      jurisdiction_code: "AR-X-CBA",
      jurisdiction_level: "municipio",
      jurisdiction_id: 2,
      jurisdiction_name: "Ciudad de Córdoba",
      applicable_laws: ["Ordenanza 12.345"],
      total_documents: 5,
      missing: 5,
      downloaded: 0,
      processed: 0,
      coverage_percentage: 0,
      by_type: { presupuesto_anual: { total: 1, missing: 1, downloaded: 0, processed: 0 } },
    },
    {
      jurisdiction_key: "nacion",
      jurisdiction_code: "AR",
      jurisdiction_level: "nacion",
      jurisdiction_id: 100,
      jurisdiction_name: "Nación Argentina",
      applicable_laws: ["Ley 27.275 (Acceso a la Información Pública)"],
      total_documents: 5,
      missing: 3,
      downloaded: 1,
      processed: 1,
      coverage_percentage: 20,
      by_type: {
        presupuesto_anual: { total: 1, missing: 0, downloaded: 0, processed: 1 },
        ejecucion_trimestral: { total: 2, missing: 1, downloaded: 1, processed: 0 },
      },
    },
    {
      jurisdiction_key: "cordoba_provincia",
      jurisdiction_code: "AR-X",
      jurisdiction_level: "provincia",
      jurisdiction_id: 1,
      jurisdiction_name: "Provincia de Córdoba",
      applicable_laws: ["Ley Provincial 8803 (Transparencia y Acceso a la Información)"],
      total_documents: 12,
      missing: 11,
      downloaded: 0,
      processed: 1,
      coverage_percentage: 8.33,
      by_type: {},
    },
  ],
}

beforeEach(() => {
  hookState.data = OVERVIEW
  hookState.isLoading = false
  hookState.error = null
})

describe("getJurisdictionLevel", () => {
  it("usa jurisdiction_level del API", () => {
    expect(getJurisdictionLevel({ jurisdiction_code: "X", jurisdiction_level: "provincia" })).toBe("provincia")
  })

  it("deduce el nivel del código real o de la clave de config (API vieja)", () => {
    expect(getJurisdictionLevel({ jurisdiction_code: "AR" })).toBe("nacion")
    expect(getJurisdictionLevel({ jurisdiction_code: "AR-X" })).toBe("provincia")
    expect(getJurisdictionLevel({ jurisdiction_code: "AR-X-CBA" })).toBe("municipio")
    expect(getJurisdictionLevel({ jurisdiction_code: "nacion" })).toBe("nacion")
    expect(getJurisdictionLevel({ jurisdiction_code: "cordoba_provincia" })).toBe("provincia")
    expect(getJurisdictionLevel({ jurisdiction_code: "cordoba_ciudad" })).toBe("municipio")
  })
})

describe("TransparencyMap", () => {
  it("etiqueta nación / provincia / ciudad y ordena por nivel", () => {
    render(<TransparencyMap />)
    const levels = screen.getAllByTestId("jurisdiction-level").map((el) => el.textContent)
    expect(levels).toEqual(["Nación", "Provincia", "Ciudad / Municipio"])
  })

  it("muestra cobertura global y badges por jurisdicción desde el overview", () => {
    render(<TransparencyMap />)
    expect(screen.getByTestId("overall-coverage").textContent).toContain("(2/22)")
    const nacion = screen.getByTestId("jurisdiction-AR")
    expect(within(nacion).getByText("20%")).toBeTruthy()
  })

  it("al expandir muestra leyes aplicables y documentos por tipo", () => {
    render(<TransparencyMap />)
    const nacion = screen.getByTestId("jurisdiction-AR")
    fireEvent.click(within(nacion).getByText("Nación Argentina"))

    expect(within(nacion).getByText("Ley 27.275 (Acceso a la Información Pública)")).toBeTruthy()
    const byType = within(nacion).getByTestId("by-type-list")
    expect(within(byType).getByText("presupuesto anual")).toBeTruthy()
    expect(within(byType).getByText("1/1")).toBeTruthy()
    expect(within(byType).getByText("1/2")).toBeTruthy()
  })

  it("jurisdicción sin docs muestra mensaje accionable en vez de vacío", () => {
    render(<TransparencyMap />)
    const provincia = screen.getByTestId("jurisdiction-AR-X")
    fireEvent.click(within(provincia).getByText("Provincia de Córdoba"))
    expect(within(provincia).getByTestId("by-type-empty")).toBeTruthy()
  })

  it("error del API muestra mensaje en vez de ocultar la card", () => {
    hookState.data = undefined
    hookState.error = new Error("boom")
    render(<TransparencyMap />)
    expect(screen.getByText(/No se pudo cargar el inventario/)).toBeTruthy()
  })

  it("inventario vacío (sin sync) lo avisa", () => {
    hookState.data = {
      ...OVERVIEW,
      total_documents: 0,
      total_processed: 0,
      overall_coverage: 0,
      jurisdictions: OVERVIEW.jurisdictions.map((j) => ({ ...j, total_documents: 0, by_type: {} })),
    }
    render(<TransparencyMap />)
    expect(screen.getByTestId("inventory-empty")).toBeTruthy()
  })
})
