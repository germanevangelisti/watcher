import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, within } from "@testing-library/react"
import { TransparencyMap } from "@/components/features/transparency-map"
import { getJurisdictionLevel } from "@/lib/jurisdiction-level"
import { fileTypeRows, legalTypeRows } from "@/lib/file-type"
import type { JurisdictionSummary, TransparencyOverview } from "@/lib/api/hooks/use-transparency"

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
      applicable_laws: [
        {
          name: "Ley 25.917 Art. 7 (aplica por adhesión provincial)",
          official_url: "https://servicios.infoleg.gob.ar/infolegInternet/anexos/95000-99999/97698/texact.htm",
        },
        { name: "Ordenanza Municipal de Transparencia", official_url: null },
      ],
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
      applicable_laws: [
        {
          name: "Ley 27.275 (Acceso a la Información Pública)",
          official_url: "https://servicios.infoleg.gob.ar/infolegInternet/anexos/265000-269999/265949/norma.htm",
        },
      ],
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
      applicable_laws: [
        {
          name: "Ley 25.917 Art. 7 (Federal de Responsabilidad Fiscal)",
          official_url: "https://servicios.infoleg.gob.ar/infolegInternet/anexos/95000-99999/97698/texact.htm",
        },
        { name: "Ley Provincial 8803 (Transparencia y Acceso a la Información)", official_url: null },
      ],
      total_documents: 12,
      missing: 11,
      downloaded: 0,
      processed: 1,
      coverage_percentage: 8.33,
      by_type: {},
    },
  ],
}

/**
 * Mismo overview pero con el eje primario del contrato 1.1.0 (`by_file_type` +
 * `file_type_taxonomy`). Los conteos son los reales del config: 5 / 12 / 5.
 * En Nación los buckets van a propósito en orden invertido (xlsx, csv, pdf): el
 * orden que se muestra tiene que salir de la taxonomía, no del orden de las claves.
 */
const FILE_TYPE_OVERVIEW: TransparencyOverview = {
  ...OVERVIEW,
  file_type_taxonomy: [
    { key: "pdf", label: "PDF" },
    { key: "csv", label: "CSV" },
    { key: "xlsx", label: "XLSX" },
  ],
  jurisdictions: OVERVIEW.jurisdictions.map((j): JurisdictionSummary => {
    if (j.jurisdiction_code === "AR") {
      return {
        ...j,
        by_file_type: {
          xlsx: { total: 1, missing: 1, downloaded: 0, processed: 0, legal_categories: { empleo_publico: 1 } },
          csv: { total: 2, missing: 1, downloaded: 1, processed: 0, legal_categories: { ejecucion_trimestral: 2 } },
          pdf: { total: 2, missing: 1, downloaded: 0, processed: 1, legal_categories: { presupuesto_anual: 1, deuda_publica: 1 } },
        },
      }
    }
    if (j.jurisdiction_code === "AR-X") {
      return {
        ...j,
        by_file_type: {
          pdf: {
            total: 4, missing: 3, downloaded: 0, processed: 1,
            legal_categories: {
              presupuesto_anual: 1, presupuesto_plurianual: 1, deuda_publica: 1, cuenta_inversion: 1,
            },
          },
          csv: {
            total: 6, missing: 6, downloaded: 0, processed: 0,
            legal_categories: { ejecucion_trimestral: 4, deuda_flotante: 1, servicios_deuda: 1 },
          },
          xlsx: { total: 2, missing: 2, downloaded: 0, processed: 0, legal_categories: { empleo_publico: 2 } },
        },
      }
    }
    return {
      ...j,
      by_file_type: {
        pdf: {
          total: 3, missing: 3, downloaded: 0, processed: 0,
          legal_categories: { presupuesto_anual: 1, deuda_municipal: 1, boletin_municipal: 1 },
        },
        csv: { total: 1, missing: 1, downloaded: 0, processed: 0, legal_categories: { ejecucion_trimestral: 1 } },
        xlsx: { total: 1, missing: 1, downloaded: 0, processed: 0, legal_categories: { empleo_publico: 1 } },
      },
    }
  }),
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

  it("ley con URL oficial es un link externo seguro (target/rel)", () => {
    render(<TransparencyMap />)
    const nacion = screen.getByTestId("jurisdiction-AR")
    fireEvent.click(within(nacion).getByText("Nación Argentina"))

    const link = within(nacion).getByTestId("law-link")
    expect(link.getAttribute("href")).toBe(
      "https://servicios.infoleg.gob.ar/infolegInternet/anexos/265000-269999/265949/norma.htm"
    )
    expect(link.getAttribute("target")).toBe("_blank")
    expect(link.getAttribute("rel")).toBe("noopener noreferrer")
    expect(link.textContent).toContain("Ley 27.275 (Acceso a la Información Pública)")
  })

  it("ley sin URL oficial muestra el nombre + 'sin URL' y ningún link", () => {
    render(<TransparencyMap />)
    const provincia = screen.getByTestId("jurisdiction-AR-X")
    fireEvent.click(within(provincia).getByText("Provincia de Córdoba"))

    const sinUrl = within(provincia).getByTestId("law-sin-url")
    expect(sinUrl.textContent).toContain("Ley Provincial 8803")
    expect(sinUrl.textContent).toContain("sin URL")
    // La ley sin fuente no se vuelve clickeable ni recibe un href inventado.
    expect(within(sinUrl).queryByRole("link")).toBeNull()
    expect(within(sinUrl).queryByTestId("law-link")).toBeNull()
  })

  it("en una misma jurisdicción conviven el link oficial y el 'sin URL'", () => {
    render(<TransparencyMap />)
    const ciudad = screen.getByTestId("jurisdiction-AR-X-CBA")
    fireEvent.click(within(ciudad).getByText("Ciudad de Córdoba"))

    expect(within(ciudad).getAllByTestId("law-link")).toHaveLength(1)
    expect(within(ciudad).getAllByTestId("law-sin-url")).toHaveLength(1)
    expect(within(ciudad).getByTestId("law-link").getAttribute("href")).toContain("infoleg.gob.ar")
  })

  it("tolera el contrato viejo (applicable_laws: string[]) sin romper", () => {
    hookState.data = {
      ...OVERVIEW,
      jurisdictions: OVERVIEW.jurisdictions.map((j) =>
        j.jurisdiction_code === "AR"
          ? { ...j, applicable_laws: ["Ley vieja sin estructura"] as unknown as typeof j.applicable_laws }
          : j
      ),
    }
    render(<TransparencyMap />)
    const nacion = screen.getByTestId("jurisdiction-AR")
    fireEvent.click(within(nacion).getByText("Nación Argentina"))

    const sinUrl = within(nacion).getByTestId("law-sin-url")
    expect(sinUrl.textContent).toContain("Ley vieja sin estructura")
    expect(sinUrl.textContent).toContain("sin URL")
    expect(within(nacion).queryAllByTestId("law-link")).toHaveLength(0)
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

describe("TransparencyMap — eje de tipos de archivo (contrato 1.1.0)", () => {
  it("el tipo de archivo es el eje primario y sale en el orden de la taxonomía", () => {
    hookState.data = FILE_TYPE_OVERVIEW
    render(<TransparencyMap />)
    const nacion = screen.getByTestId("jurisdiction-AR")
    fireEvent.click(within(nacion).getByText("Nación Argentina"))

    const list = within(nacion).getByTestId("by-file-type-list")
    expect(list.getAttribute("data-axis")).toBe("file-type")
    // El encabezado dice sobre qué eje se está contando.
    expect(within(nacion).getByTestId("by-type-heading").textContent).toBe("Documentos por tipo de archivo:")
    // El eje legal no desaparece: pasa a ser el detalle de cada tipo de archivo.
    expect(within(nacion).queryByTestId("by-type-list")).toBeNull()

    // Los buckets venían en orden invertido (xlsx, csv, pdf): manda la taxonomía.
    expect(within(list).getAllByTestId(/^type-row-/).map((el) => el.dataset.testid)).toEqual([
      "type-row-pdf",
      "type-row-csv",
      "type-row-xlsx",
    ])

    expect(within(nacion).getByTestId("type-row-pdf").textContent).toContain("PDF")
    expect(within(nacion).getByTestId("type-row-pdf").textContent).toContain("1/2")
    expect(within(nacion).getByTestId("type-row-csv").textContent).toContain("CSV")
    expect(within(nacion).getByTestId("type-row-csv").textContent).toContain("1/2")
    expect(within(nacion).getByTestId("type-row-xlsx").textContent).toContain("XLSX")
    expect(within(nacion).getByTestId("type-row-xlsx").textContent).toContain("0/1")
  })

  it("la categoría legal queda como detalle secundario dentro del tipo", () => {
    hookState.data = FILE_TYPE_OVERVIEW
    render(<TransparencyMap />)
    const provincia = screen.getByTestId("jurisdiction-AR-X")
    fireEvent.click(within(provincia).getByText("Provincia de Córdoba"))

    const csv = within(provincia).getByTestId("legal-categories-csv").textContent ?? ""
    expect(csv).toContain("ejecucion trimestral (4)")
    expect(csv).toContain("deuda flotante (1)")
    expect(csv).toContain("servicios deuda (1)")

    const pdf = within(provincia).getByTestId("type-row-pdf").textContent ?? ""
    expect(pdf).toContain("presupuesto plurianual (1)")
    expect(pdf).toContain("cuenta inversion (1)")
    expect(pdf).toContain("1/4") // 1 procesado de 4 PDF
  })

  it("los conteos del eje de archivo cierran contra el total de la jurisdicción", () => {
    hookState.data = FILE_TYPE_OVERVIEW
    render(<TransparencyMap />)

    const jurisdictions: [string, string, number][] = [
      ["jurisdiction-AR", "Nación Argentina", 5],
      ["jurisdiction-AR-X", "Provincia de Córdoba", 12],
      ["jurisdiction-AR-X-CBA", "Ciudad de Córdoba", 5],
    ]

    for (const [testId, name, totalDocuments] of jurisdictions) {
      const card = screen.getByTestId(testId)
      fireEvent.click(within(card).getByText(name))

      const rows = within(card).getAllByTestId(/^type-row-/)
      expect(rows).toHaveLength(3)
      // "disponibles/total" de cada tipo de archivo: tiene que sumar el total de la
      // jurisdicción (un documento cae en un solo bucket, no se cuenta dos veces).
      const totals = rows.map((el) => Number(el.textContent?.match(/(\d+)\/(\d+)/)?.[2]))
      expect(totals.reduce((sum, n) => sum + n, 0)).toBe(totalDocuments)
    }
  })

  it("sin `by_file_type` (backend viejo) cae al eje legal y no rompe en silencio", () => {
    render(<TransparencyMap />) // OVERVIEW sin el campo nuevo
    const nacion = screen.getByTestId("jurisdiction-AR")
    fireEvent.click(within(nacion).getByText("Nación Argentina"))

    expect(within(nacion).queryByTestId("by-file-type-list")).toBeNull()
    const legacy = within(nacion).getByTestId("by-type-list")
    expect(legacy.getAttribute("data-axis")).toBe("legal")
    expect(within(nacion).getByTestId("by-type-heading").textContent).toBe("Documentos por tipo (categoría legal):")
    expect(within(legacy).getByText("presupuesto anual")).toBeTruthy()
    expect(within(legacy).getByText("1/1")).toBeTruthy()
  })

  it("sin entrada en la taxonomía la etiqueta cae a la clave en mayúsculas", () => {
    hookState.data = {
      ...FILE_TYPE_OVERVIEW,
      file_type_taxonomy: [{ key: "pdf", label: "PDF" }],
    }
    render(<TransparencyMap />)
    const nacion = screen.getByTestId("jurisdiction-AR")
    fireEvent.click(within(nacion).getByText("Nación Argentina"))

    expect(within(nacion).getByTestId("type-row-pdf").textContent).toContain("PDF")
    expect(within(nacion).getByTestId("type-row-csv").textContent).toContain("CSV")
  })
})

describe("fileTypeRows / legalTypeRows", () => {
  it("el detalle legal suma el total del tipo de archivo", () => {
    const [row] = fileTypeRows({
      csv: {
        total: 6, missing: 6, downloaded: 0, processed: 0,
        legal_categories: { ejecucion_trimestral: 4, deuda_flotante: 1, servicios_deuda: 1 },
      },
    })
    expect(row.total).toBe(6)
    expect(row.available).toBe(0)
    expect(row.legalCategories.reduce((sum, c) => sum + c.count, 0)).toBe(6)
    // Detalle ordenado por cantidad, y las etiquetas sin guiones bajos.
    expect(row.legalCategories.map((c) => c.label)).toEqual([
      "ejecucion trimestral",
      "deuda flotante",
      "servicios deuda",
    ])
  })

  it("ordena por taxonomía y deja el formato desconocido al final, sin descartarlo", () => {
    const rows = fileTypeRows(
      {
        docx: { total: 1, missing: 1, downloaded: 0, processed: 0, legal_categories: { otro: 1 } },
        xlsx: { total: 1, missing: 1, downloaded: 0, processed: 0, legal_categories: { empleo_publico: 1 } },
        pdf: { total: 1, missing: 1, downloaded: 0, processed: 0, legal_categories: { presupuesto_anual: 1 } },
      },
      [{ key: "pdf", label: "PDF" }, { key: "xlsx", label: "XLSX" }]
    )
    expect(rows.map((r) => r.label)).toEqual(["PDF", "XLSX", "DOCX"])
  })

  it("legalTypeRows conserva el contrato viejo (total derivado si falta)", () => {
    const rows = legalTypeRows({
      presupuesto_anual: { missing: 0, downloaded: 0, processed: 1 },
      ejecucion_trimestral: { total: 2, missing: 1, downloaded: 1, processed: 0 },
    })
    expect(rows.map((r) => [r.label, `${r.available}/${r.total}`])).toEqual([
      ["presupuesto anual", "1/1"],
      ["ejecucion trimestral", "1/2"],
    ])
    expect(rows[0].legalCategories).toEqual([])
  })
})
