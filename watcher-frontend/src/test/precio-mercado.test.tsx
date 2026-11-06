import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, within } from "@testing-library/react"
import { PrecioMercadoPage } from "@/pages/analisis/precio-mercado"
import { formatArs } from "@/lib/precio-mercado-format"
import type { AnalisisPrecio, GastoDetectadoResponse, GastoFiltros } from "@/types/precio-mercado"

/**
 * epic:precio-mercado (M8) - la pantalla lista el gasto detectado con filtros,
 * total y suma, el análisis se dispara a pedido y el resultado muestra fuentes y
 * fechas, sin dictamen.
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

/** Dos filas que cubren los dos universos: una en el ledger y otra no. */
const DETECTADO: GastoDetectadoResponse = {
  total: 3,
  suma: 186031508,
  republicaciones_excluidas: 2000,
  items: [
    {
      analisis_id: 415, ejecucion_id: 292, fuente: "provincial", fecha: "2026-04-30", boletin_id: 1,
      boletin_url: "https://boletin.example/1", organismo: "MINISTERIO DE DESARROLLO SOCIAL",
      municipio: null, nivel: "provincial", tipo_gasto: "licitacion", objeto: "bien",
      etapa_gasto: "llamado",
      concepto: "Licitación pública para la provisión de cemento portland",
      gasto_motivo: "keyword licitacion", monto: 186031008, es_gasto_publico: true,
      en_ledger: true, is_duplicate_gasto: false, ultima_clasificacion: null,
    },
    {
      analisis_id: 500, ejecucion_id: null, fuente: "municipal_capital", fecha: "2026-05-31", boletin_id: 2,
      boletin_url: null, organismo: "MUNICIPALIDAD DE CARRILOBO", municipio: "Carrilobo",
      nivel: "municipal", tipo_gasto: "licitacion", objeto: "obra", etapa_gasto: null,
      concepto: "Llamado a licitación para la obra de cordón cuneta",
      gasto_motivo: "keyword licitacion", monto: 500, es_gasto_publico: true,
      en_ledger: false, is_duplicate_gasto: true, ultima_clasificacion: null,
    },
    {
      // La compra del portal que probó Germán (WMU1): gasto clasificado, sin fila
      // de ledger y con el presupuesto oficial del llamado como monto.
      analisis_id: 12387, ejecucion_id: null, fuente: "municipal_compras", fecha: "2026-10-21",
      boletin_id: 900, boletin_url: "https://compras.cordoba.gob.ar/#/compras-publicas/listadocompras/TODOS",
      organismo: "Municipalidad de Córdoba - SECRETARÍA DE POLÍTICAS SOCIALES Y DESARROLLO HUMANO",
      municipio: "Córdoba", nivel: "municipal", tipo_gasto: "subasta_electronica", objeto: "otro",
      etapa_gasto: "llamado",
      concepto: "SERVICIO DE RACIONAMIENTO EN COCIDO",
      gasto_motivo: "portal de compras: SUBASTA ELECTRONICA INVERSA",
      monto: 2398134234.22, es_gasto_publico: true, en_ledger: false,
      is_duplicate_gasto: false, ultima_clasificacion: null,
    },
  ],
}

const COBERTURA = {
  fuentes: [
    { fuente: "provincial", nombre: "Boletín Oficial de la Provincia de Córdoba", nivel: "provincial",
      municipio: null, portal: null, tipo: "boletin" as const, detalle: null,
      ediciones: 150, desde: "2026-01-02", hasta: "2026-10-30",
      actos: 4000, actos_gasto: 900, monto_gasto: 1 },
    { fuente: "municipal_capital", nombre: "Boletín Municipal de la Ciudad de Córdoba", nivel: "municipal",
      municipio: "Córdoba", portal: null, tipo: "boletin" as const, detalle: null,
      ediciones: 80, desde: "2026-01-02", hasta: "2026-11-03",
      actos: 504, actos_gasto: 12, monto_gasto: 1 },
    { fuente: "municipal_compras", nombre: "Portal de Compras de la Ciudad de Córdoba (MuniCompras)",
      nivel: "municipal", municipio: "Córdoba", portal: "https://compras.cordoba.gob.ar",
      tipo: "portal" as const,
      detalle: "El monto es el presupuesto oficial del llamado: el adjudicatario y el monto adjudicado no son públicos.",
      ediciones: 97, desde: "2026-01-07", hasta: "2026-11-04",
      actos: 153, actos_gasto: 151, monto_gasto: 49600000000 },
  ],
  municipios_cubiertos: ["Córdoba"],
  nota: "Los demás municipios y comunas sólo aparecen cuando publican en la sección 5 del boletín provincial; su gasto propio no está cubierto.",
}

/** Filtros con los que la pantalla pidió el listado, en orden. */
const llamadas: GastoFiltros[] = []

vi.mock("@/lib/api", () => ({
  useGastoDetectado: (filtros: GastoFiltros) => {
    llamadas.push(filtros)
    return { data: DETECTADO, isLoading: false, isError: false }
  },
  useAnalizarPrecio: () => analizarState,
  useCoberturaGasto: () => ({ data: COBERTURA }),
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
  llamadas.length = 0
  analizarState = { mutate, isPending: false, isError: false }
})

describe("pantalla gasto detectado", () => {
  it("lista el gasto con su tipo y nivel, y muestra total y suma", () => {
    render(<PrecioMercadoPage />)
    const tabla = screen.getByTestId("gasto-detectado")
    // Dos ejes: la figura (procedimiento) y el objeto de lo que se compra.
    expect(within(tabla).getAllByText("Licitación").length).toBe(2)
    expect(within(tabla).getByText("Provincia")).toBeTruthy()
    expect(within(tabla).getByText("Bienes")).toBeTruthy()
    expect(within(tabla).getByText("Obra")).toBeTruthy()
    expect(within(tabla).getByText("Carrilobo")).toBeTruthy()
    // Lo que el ciudadano lee para elegir es el acto, no el motivo de la clasificación.
    expect(within(tabla).getByText(/provisión de cemento portland/)).toBeTruthy()
    expect(screen.getByTestId("totales").textContent).toContain("3 actos")
    expect(screen.getByTestId("totales").textContent).toContain(formatArs(DETECTADO.suma))
  })

  it("la etapa del gasto se ve: el monto del portal es el presupuesto del llamado", () => {
    render(<PrecioMercadoPage />)
    const etapas = screen.getAllByTestId("etapa-gasto")
    expect(etapas[0].textContent).toBe("Llamado")
    expect(etapas[1].textContent).toBe("-") // sin etapa declarada
    expect(etapas[2].textContent).toContain("Llamado")
    expect(etapas[2].textContent).toContain("presupuesto oficial")
  })

  it("el link dice de dónde salió el acto: portal de compras, no boletín oficial", () => {
    render(<PrecioMercadoPage />)
    const tabla = screen.getByTestId("gasto-detectado")
    expect(within(tabla).getAllByText("Portal de compras").length).toBe(1)
    expect(within(tabla).getAllByText("Boletín oficial").length).toBe(1)
    const link = within(tabla).getByText("Portal de compras")
    expect(link.getAttribute("href")).toContain("compras.cordoba.gob.ar")
  })

  it("una compra del portal se declara fuera del ledger y explica por qué no se analiza", () => {
    render(<PrecioMercadoPage />)
    // Dos filas sin fila de ledger: la del municipio y la del portal.
    expect(screen.getAllByTestId("fuera-del-ledger").length).toBe(2)
    const botones = screen.getAllByRole("button", { name: "Analizar en profundidad" })
    expect(botones[2]).toHaveProperty("disabled", true)
    expect(botones[2].getAttribute("title")).toContain("renglones")
    expect(botones[2].getAttribute("title")).toContain("cantidades")
    fireEvent.click(botones[2])
    expect(mutate).not.toHaveBeenCalled()
  })

  it("sin descripción cae al motivo, para no dejar la celda vacía", () => {
    const original = DETECTADO.items[0].concepto
    DETECTADO.items[0].concepto = null
    try {
      render(<PrecioMercadoPage />)
      expect(within(screen.getByTestId("gasto-detectado")).getAllByText("keyword licitacion").length).toBeGreaterThan(0)
    } finally {
      DETECTADO.items[0].concepto = original
    }
  })

  it("declara la republicación en vez de sumarla en silencio", () => {
    render(<PrecioMercadoPage />)
    expect(screen.getByTestId("republicaciones").textContent).toContain(formatArs(2000))
    expect(within(screen.getByTestId("gasto-detectado")).getByText("republicación")).toBeTruthy()
  })

  it("el análisis se dispara solo cuando el usuario lo pide", () => {
    render(<PrecioMercadoPage />)
    expect(mutate).not.toHaveBeenCalled()
    fireEvent.click(screen.getAllByRole("button", { name: "Analizar en profundidad" })[0])
    expect(mutate).toHaveBeenCalledWith(292)
  })

  it("no ofrece analizar un acto que no está en el ledger, y dice por qué", () => {
    render(<PrecioMercadoPage />)
    const botones = screen.getAllByRole("button", { name: "Analizar en profundidad" })
    expect(botones[1]).toHaveProperty("disabled", true)
    expect(botones[1].getAttribute("title")).toContain("no está en el ledger")
    fireEvent.click(botones[1])
    expect(mutate).not.toHaveBeenCalled()
  })

  it("los filtros viajan al hook", () => {
    const ultimo = () => llamadas[llamadas.length - 1]
    render(<PrecioMercadoPage />)
    // Sin filtro explícito, el listado pide solo gasto.
    expect(ultimo()).toEqual(expect.objectContaining({ solo_gasto: true }))

    fireEvent.change(screen.getByTestId("filtro-tipo"), { target: { value: "compra_directa" } })
    fireEvent.change(screen.getByTestId("filtro-objeto"), { target: { value: "obra" } })
    fireEvent.change(screen.getByTestId("filtro-nivel"), { target: { value: "municipal" } })
    fireEvent.change(screen.getByTestId("filtro-organismo"), { target: { value: "CARRILOBO" } })
    fireEvent.change(screen.getByTestId("filtro-desde"), { target: { value: "2026-05-01" } })
    fireEvent.change(screen.getByTestId("filtro-monto-min"), { target: { value: "1000" } })

    expect(ultimo()).toEqual(expect.objectContaining({
      tipo: "compra_directa", objeto: "obra", nivel: "municipal", organismo: "CARRILOBO",
      fecha_desde: "2026-05-01", monto_min: "1000", solo_gasto: true,
    }))

    fireEvent.click(screen.getByTestId("filtro-solo-gasto"))
    expect(ultimo()).toEqual(expect.objectContaining({ solo_gasto: false }))
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

describe("renglones de ComprasCba", () => {
  it("muestra el proceso y las cantidades por renglón del pliego", () => {
    analizarState = {
      ...analizarState,
      data: {
        ...RESULTADO,
        extraccion: {
          ...RESULTADO.extraccion,
          renglones: [
            { numero: 1, descripcion: "Resmas de papel A4", cantidad: 12000, precio_referencia: null, presupuesto: null },
            { numero: 3, descripcion: "Libros de actas", cantidad: 5880, precio_referencia: null, presupuesto: null },
          ],
          proceso: { nro: "1/2026", tipo: "Licitación Presencial", servicio: "199 - Policia", objeto: "RESMAS", estado: "ADJUDICADA",
            presupuesto_total: 186031008, fecha_limite: "13/05/2026", documento: "pliego.pdf", origen: "pliego", url: "https://portal", motivo: null },
        },
      },
    }
    render(<PrecioMercadoPage />)
    const proceso = screen.getByTestId("proceso-compras")
    expect(within(proceso).getByText("1/2026")).toBeTruthy()
    expect(within(screen.getByTestId("renglones")).getByText("12000")).toBeTruthy()
    expect(proceso.textContent).toContain("pliego.pdf")
  })

  it("muestra el análisis por renglón con su clasificación y el agregado", () => {
    const cmp = { clasificacion: "sin_datos_suficientes" as const, motivo: "solo se conoce el monto total del acto", mediana: 8000, desvio: null, n_referencias: 3 }
    analizarState = {
      ...analizarState,
      data: {
        ...RESULTADO,
        renglones_analisis: [
          { numero: 1, item: "Resmas de papel A4", cantidad: 12000, unidad: "resmas", precio_unitario: null, origen_precio: null,
            comparacion: cmp, fuentes: [],
            referencias: [{ source: "Mercado Libre", description: "Pack 5 Resmas (pack de 5: precio ÷ 5)", unit_price: 8000,
              observed_on: "2026-10-12", url: null, quantity: 5, unit: "resmas", kind: "externa" }] },
          { numero: 2, item: "Libros de actas", cantidad: 5880, unidad: "libros", precio_unitario: 3000, origen_precio: "precio de referencia del proceso",
            comparacion: { ...cmp, clasificacion: "dentro_de_rango", motivo: null, mediana: 3500, desvio: -0.14 }, fuentes: [], referencias: [] },
        ],
        agregado: { renglones: 2, por_clasificacion: {}, monto_total_acto: 186031008, estimado_mercado: 116580000,
          desvio: 0.6, clasificacion: "observable", motivo: null, nota: "estimado = suma" },
      },
    }
    render(<PrecioMercadoPage />)
    const rows = screen.getAllByTestId("renglon-analisis")
    expect(rows).toHaveLength(2)
    expect(rows[0].textContent).toContain("solo monto total")
    expect(rows[0].textContent).toContain("12000 resmas")
    expect(rows[1].textContent).toContain("-14%")
    expect(screen.getByTestId("agregado-renglones").textContent).toContain("60%")
  })
})


describe("PrecioMercadoPage - cobertura", () => {
  it("muestra las fuentes cubiertas y lo que queda afuera", () => {
    render(<PrecioMercadoPage />)
    const banner = screen.getByTestId("cobertura-banner")
    expect(within(banner).getByText("Boletín Municipal de la Ciudad de Córdoba")).toBeTruthy()
    expect(banner.textContent).toContain("80 ediciones")
    expect(banner.textContent).toContain("sección 5")
  })

  it("suma el portal de compras con su unidad y lo que no publica", () => {
    render(<PrecioMercadoPage />)
    const banner = screen.getByTestId("cobertura-banner")
    expect(within(banner).getByText("Portal de Compras de la Ciudad de Córdoba (MuniCompras)")).toBeTruthy()
    // Un portal no tiene "ediciones": tiene días de publicación y compras.
    expect(banner.textContent).toContain("97 días con publicaciones · 153 compras · 151 con monto")
    expect(banner.textContent).toContain("no son públicos")
  })
})

describe("PrecioMercadoPage - llega desde el mapa (WMA1)", () => {
  afterEach(() => {
    window.history.replaceState({}, "", "/")
  })

  it("filtra por el código de la jurisdicción y no por el nombre", () => {
    window.history.pushState(
      {},
      "",
      "/analisis/precio-mercado?municipio=R%C3%ADo+Ceballos&municipio_codigo=140147",
    )
    render(<PrecioMercadoPage />)

    const ultimo = llamadas[llamadas.length - 1]
    // El código une "Rio Ceballos" y "Río Ceballos": mandar los dos filtros
    // dejaría afuera las grafías sin acento.
    expect(ultimo).toEqual(expect.objectContaining({ municipio_codigo: "140147" }))
    expect(ultimo).not.toHaveProperty("municipio")

    const chip = screen.getByTestId("filtro-jurisdiccion")
    expect(chip.textContent).toContain("Río Ceballos")

    fireEvent.click(within(chip).getByRole("button", { name: "Ver toda la provincia" }))
    expect(llamadas[llamadas.length - 1]).not.toHaveProperty("municipio_codigo")
    expect(screen.queryByTestId("filtro-jurisdiccion")).toBeNull()
  })
})
