import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, within } from "@testing-library/react"
import { PrecioMercadoPage } from "@/pages/analisis/precio-mercado"
import { formatArs } from "@/lib/precio-mercado-format"
import type { AnalisisPrecio } from "@/types/precio-mercado"

/**
 * epic:precio-mercado - la pantalla lista los gastos observables, el análisis
 * se dispara a pedido y el resultado muestra fuentes y fechas, sin dictamen.
 */

const mutate = vi.fn()
let analizarState: { mutate: typeof mutate; isPending: boolean; isError: boolean; data?: AnalisisPrecio } = {
  mutate, isPending: false, isError: false,
}

const OBSERVABLES = {
  total: 1,
  items: [{
    id: 415, fecha: "2026-04-30", organismo: "MINISTERIO DE DESARROLLO SOCIAL",
    concepto: "ADQUISICION DE RESMAS DE PAPEL Y LIBROS DE ACTAS", monto: 186031008,
    tipo_operacion: "licitacion", etapa_gasto: "llamado", boletin_id: 292,
    boletin_url: "https://boletin.example/1", motivo: "compra de bien estandarizable: «resma»",
    ultima_clasificacion: null,
  }],
}

vi.mock("@/lib/api", () => ({
  useObservables: () => ({ data: OBSERVABLES, isLoading: false, isError: false }),
  useAnalizarPrecio: () => analizarState,
}))

const RESULTADO: AnalisisPrecio = {
  acto: OBSERVABLES.items[0],
  extraccion: { item: "resmas de papel", cantidad: null, unidad: null, monto_total: 186031008, metodo: "llm" },
  precio_unitario: null,
  comparacion: { clasificacion: "sin_datos_suficientes", motivo: "el acto no declara una cantidad extraíble", mediana: null, desvio: null, n_referencias: 0 },
  umbrales: { observable: 0.3, alerta: 1, min_references: 3 },
  fuentes: [
    { fuente: "corpus", disponible: true, referencias: 0, motivo: "1 actos similares en el corpus, ninguno con cantidad extraíble" },
    { fuente: "mercadolibre", disponible: false, referencias: 0, motivo: "no disponible: la API de Mercado Libre exige un token (ML_ACCESS_TOKEN)" },
  ],
  referencias: [],
  proveedor_llm: "ollama:qwen2.5:7b",
  aviso: "Comparación orientativa con fuentes y fechas. No constituye dictamen.",
}

beforeEach(() => {
  mutate.mockReset()
  analizarState = { mutate, isPending: false, isError: false }
})

describe("pantalla precio de mercado", () => {
  it("lista los gastos observables con monto y motivo", () => {
    render(<PrecioMercadoPage />)
    const tabla = screen.getByTestId("observables")
    expect(within(tabla).getByText(/RESMAS DE PAPEL/)).toBeTruthy()
    expect(within(tabla).getByText(/«resma»/)).toBeTruthy()
    expect(screen.getByText("1 actos detectados")).toBeTruthy()
  })

  it("el análisis se dispara solo cuando el usuario lo pide", () => {
    render(<PrecioMercadoPage />)
    expect(mutate).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole("button", { name: "Analizar" }))
    expect(mutate).toHaveBeenCalledWith(415)
  })

  it("muestra clasificación, fuentes caídas y aviso sin dictamen", () => {
    analizarState = { ...analizarState, data: RESULTADO }
    render(<PrecioMercadoPage />)
    const res = screen.getByTestId("resultado-analisis")
    expect(within(res).getByTestId("clasificacion").textContent).toBe("Sin datos suficientes")
    expect(within(res).getByText("no declarada")).toBeTruthy()
    expect(within(res).getByTestId("fuentes").textContent).toContain("mercadolibre: no disponible")
    expect(within(res).getByTestId("aviso").textContent).toContain("No constituye dictamen")
    expect(res.textContent?.toLowerCase()).not.toContain("sobreprecio")
  })

  it("muestra referencias con fuente y fecha", () => {
    analizarState = {
      ...analizarState,
      data: {
        ...RESULTADO,
        precio_unitario: 30000,
        comparacion: { clasificacion: "alerta", motivo: null, mediana: 10000, desvio: 2, n_referencias: 3 },
        referencias: [{ source: "Boletín oficial - A", description: "1.000 resmas", unit_price: 10000, observed_on: "2026-03-01", url: null, quantity: 1000, unit: "resmas", kind: "interna" }],
      },
    }
    render(<PrecioMercadoPage />)
    const refs = screen.getByTestId("referencias")
    expect(within(refs).getByText("2026-03-01")).toBeTruthy()
    expect(within(refs).getByText("Boletín oficial - A")).toBeTruthy()
    expect(screen.getByTestId("clasificacion").textContent).toBe("Alerta")
    expect(screen.getByText("200%")).toBeTruthy()
  })

  it("formatea pesos y ausencia de valor", () => {
    expect(formatArs(null)).toBe("-")
    expect(formatArs(1000)).toContain("1.000")
  })
})
