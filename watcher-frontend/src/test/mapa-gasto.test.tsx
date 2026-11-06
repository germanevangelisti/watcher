import { describe, it, expect, vi, beforeEach } from "vitest"
import { act, fireEvent, render, screen, within } from "@testing-library/react"
import { MapaGastoPage } from "@/pages/analisis/mapa-gasto"
import {
  construirClases,
  construirFeatureCollection,
  expresionColor,
  popupHtml,
} from "@/lib/mapa-gasto"
import type { FeatureCollectionGeo, GastoPorJurisdiccionResponse, JurisdiccionGasto } from "@/types/mapa-gasto"

/**
 * WMA1 — mapa de gasto por jurisdicción.  MapLibre no corre en happy-dom (necesita
 * WebGL), así que se mockea el motor y se testea lo que decide el producto: la
 * leyenda con histograma, el gris de "sin datos", el filtro de tamaño, el
 * click-through al listado y la unión GeoJSON ↔ respuesta del API.
 */

type Handler = (...args: unknown[]) => void

const mocks = vi.hoisted(() => ({
  mapas: [] as { handlers: Record<string, Handler[]> }[],
  popups: [] as string[],
  setData: vi.fn(),
  setPaintProperty: vi.fn(),
  setFilter: vi.fn(),
  addLayer: vi.fn(),
  addSource: vi.fn(),
}))

vi.mock("maplibre-gl", () => {
  class Popup {
    setLngLat() { return this }
    setHTML(html: string) { mocks.popups.push(html); return this }
    addTo() { return this }
  }
  class MapMock {
    opciones: unknown
    handlers: Record<string, Handler[]> = {}
    constructor(opciones: unknown) {
      this.opciones = opciones
      mocks.mapas.push(this)
    }
    on(evento: string, capaOCallback: unknown, callback?: Handler) {
      const clave = typeof capaOCallback === "string" ? `${evento}:${capaOCallback}` : evento
      const fn = (typeof capaOCallback === "function" ? capaOCallback : callback) as Handler
      ;(this.handlers[clave] ||= []).push(fn)
      return this
    }
    addControl() { return this }
    addSource(id: string, def: unknown) { mocks.addSource(id, def); return this }
    addLayer(def: unknown) { mocks.addLayer(def); return this }
    getSource() { return { setData: mocks.setData } }
    setPaintProperty(...args: unknown[]) { mocks.setPaintProperty(...args); return this }
    setFilter(...args: unknown[]) { mocks.setFilter(...args); return this }
    getCanvas() { return { style: {} as Record<string, string> } }
    remove() { return undefined }
  }
  return {
    default: { Map: MapMock, Popup, NavigationControl: class {}, AttributionControl: class {} },
    Map: MapMock,
    Popup,
    NavigationControl: class {},
    AttributionControl: class {},
  }
})

const JURISDICCIONES: JurisdiccionGasto[] = [
  {
    codigo: "140147", nombre: "Río Ceballos", tipo: "municipio", departamento: "Colón",
    nivel: "municipal", poblacion_2022: 27136, actos: 29, republicaciones: 3,
    gasto: 700323430, gasto_per_capita: 25807.91, cobertura: true,
  },
  {
    codigo: "142182", nombre: "Las Cañadas", tipo: "comuna", departamento: "Cruz del Eje",
    nivel: "comunal", poblacion_2022: 295, actos: 45, republicaciones: 0,
    gasto: 3764058194, gasto_per_capita: 12759519.3, cobertura: true,
  },
  {
    codigo: "140077", nombre: "Córdoba", tipo: "municipio", departamento: "Capital",
    nivel: "municipal", poblacion_2022: 1505250, actos: 0, republicaciones: 0,
    gasto: 0, gasto_per_capita: null, cobertura: false,
  },
  {
    codigo: "142448", nombre: "Leguizamón", tipo: "comuna", departamento: "Presidente Roque Sáenz Peña",
    nivel: "comunal", poblacion_2022: 35, actos: 0, republicaciones: 0,
    gasto: 0, gasto_per_capita: null, cobertura: false,
  },
]

const DATA: GastoPorJurisdiccionResponse = {
  jurisdicciones: JURISDICCIONES,
  por_nivel: [
    { nivel: "comunal", actos: 45, gasto: 3764058194 },
    { nivel: "municipal", actos: 29, gasto: 700323430 },
    { nivel: "provincial", actos: 730, gasto: 1694806111867.76 },
  ],
  sin_jurisdiccion: { actos: 18, gasto: 5617254856.95, niveles: ["municipal"] },
  totales: { actos: 74, gasto: 4464381624, con_cobertura: 2, jurisdicciones: 4 },
  fuente: {
    catalogo: "ReFeGLo (Ministerio del Interior)",
    poblacion: "Censo Nacional de Población, Hogares y Viviendas 2022 (INDEC)",
    limites: "OpenStreetMap, admin_level=7 (© OpenStreetMap contributors, ODbL)",
    fecha: "2026-11-06",
    nota: "El gris no es gasto cero.",
  },
}

const GEOJSON: FeatureCollectionGeo = {
  type: "FeatureCollection",
  features: JURISDICCIONES.map((j, i) => ({
    type: "Feature",
    properties: { codigo: j.codigo, nombre: j.nombre, tipo: j.tipo },
    geometry: { type: "Point", coordinates: [-64 + i, -31] },
  })),
}

vi.mock("@/lib/api", () => ({
  useGastoPorJurisdiccion: () => ({ data: DATA, isLoading: false, isError: false }),
}))

beforeEach(() => {
  mocks.mapas.length = 0
  mocks.popups.length = 0
  mocks.setData.mockClear()
  mocks.setPaintProperty.mockClear()
  mocks.setFilter.mockClear()
  mocks.addLayer.mockClear()
  mocks.addSource.mockClear()
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => GEOJSON })))
})

/** Crea el mapa y dispara el `load`, que es donde se agrega la fuente. */
async function cargarMapa() {
  const utils = render(<MapaGastoPage />)
  await act(async () => {
    await mocks.mapas[0]?.handlers.load?.[0]?.()
  })
  return { ...utils, mapa: mocks.mapas[0] }
}

describe("mapa de gasto por jurisdicción", () => {
  it("dibuja los límites estáticos con el gasto y el gris de sin datos", async () => {
    await cargarMapa()
    expect(mocks.addSource).toHaveBeenCalledWith("jurisdicciones", expect.objectContaining({ type: "geojson" }))

    const capas = mocks.addLayer.mock.calls.map(([def]) => (def as { id: string }).id)
    expect(capas).toContain("jurisdicciones-fill")

    // La expresión pinta gris las jurisdicciones sin actos, no el azul más bajo.
    const expresion = mocks.addLayer.mock.calls[0][0].paint["fill-color"]
    expect(JSON.stringify(expresion)).toContain('#3a3a37')
  })

  it("la leyenda dice el rango de cada clase, cuántas áreas caen y cuántas no tienen datos", async () => {
    await cargarMapa()
    const leyenda = screen.getByTestId("leyenda")
    const clases = within(leyenda).getAllByTestId("clase")
    // Dos jurisdicciones con datos: las clases se colapsan, no se inventan rangos vacíos.
    const total = clases.reduce((suma, fila) => {
      const texto = within(fila).getByTestId("clase-count").textContent ?? ""
      return suma + Number(texto.split(" ")[0])
    }, 0)
    expect(total).toBe(2)
    expect(within(leyenda).getByTestId("clase-sin-datos").textContent).toContain("2 áreas")
    expect(leyenda.textContent).toContain("Gasto detectado")
  })

  it("cambiar la métrica repinta sin recrear el mapa", async () => {
    const { mapa } = await cargarMapa()
    fireEvent.change(screen.getByTestId("metrica-select"), { target: { value: "per_capita" } })
    expect(mocks.mapas.length).toBe(1)
    expect(mapa).toBe(mocks.mapas[0])
    expect(mocks.setPaintProperty).toHaveBeenCalled()
    expect(screen.getByTestId("leyenda").textContent).toContain("Gasto per cápita")
  })

  it("el filtro por tamaño achica el conjunto visible", async () => {
    await cargarMapa()
    expect(screen.getByTestId("filtro-count").textContent).toContain("2 de 4 jurisdicciones con datos")
    fireEvent.change(screen.getByTestId("tamano-select"), { target: { value: "grande" } })
    // Sólo Córdoba capital supera los 50.000 y no tiene actos.
    expect(screen.getByTestId("filtro-count").textContent).toContain("0 de 1 jurisdicciones con datos")
  })

  it("click en un área abre el popup con el link al listado de esa jurisdicción", async () => {
    const { mapa } = await cargarMapa()
    await act(async () => {
      mapa.handlers["click:jurisdicciones-fill"]?.[0]?.({
        features: [{ properties: { codigo: "140147" } }],
        lngLat: { lat: -31.3, lng: -64.5 },
      })
    })
    expect(mocks.popups).toHaveLength(1)
    expect(mocks.popups[0]).toContain("Río Ceballos")
    expect(mocks.popups[0]).toContain("/analisis/precio-mercado?")
    expect(mocks.popups[0]).toContain("municipio_codigo=140147")
  })

  it("dice de dónde salen los límites y la población", async () => {
    await cargarMapa()
    const fuente = screen.getByTestId("fuente-mapa").textContent ?? ""
    expect(fuente).toContain("OpenStreetMap")
    expect(fuente).toContain("Censo Nacional de Población")
    expect(fuente).toContain("2026-11-06")
  })
})

describe("helpers del mapa", () => {
  it("sin datos no es gasto cero: el popup lo dice", () => {
    const html = popupHtml(JURISDICCIONES[2])
    expect(html).toContain("Córdoba")
    expect(html).toContain("no es gasto cero")
    expect(html).not.toContain("Per cápita")
  })

  it("el popup usa las clases que pinta el CSS del tema oscuro", () => {
    const conDatos = popupHtml(JURISDICCIONES[0])
    const sinDatos = popupHtml(JURISDICCIONES[2])
    for (const clase of ["mapa-popup-contenido", "mapa-popup-meta", "mapa-popup-link"]) {
      expect(conDatos).toContain(clase)
    }
    expect(conDatos).toContain("mapa-popup-datos")
    expect(sinDatos).toContain("mapa-popup-sin-datos")
    // Sin datos no muestra la grilla de números, sólo la aclaración.
    expect(sinDatos).not.toContain("mapa-popup-datos")
  })

  it("la colección une el GeoJSON con la respuesta y marca los filtrados", () => {
    const fc = construirFeatureCollection(GEOJSON, JURISDICCIONES, "gasto", "grande")
    const porCodigo = Object.fromEntries(fc.features.map((f) => [f.properties.codigo, f.properties]))
    expect(porCodigo["140147"].valor).toBe(700323430)
    expect(porCodigo["140147"].visible).toBe(false) // 27.136 hab. < 50.000
    expect(porCodigo["140077"].visible).toBe(true) // 1.505.250 hab.
    expect(porCodigo["140077"].cobertura).toBe(false)
  })

  it("la escala usa cuantiles sólo sobre las jurisdicciones con datos", () => {
    const clases = construirClases(JURISDICCIONES, "gasto")
    expect(clases.reduce((suma, c) => suma + c.count, 0)).toBe(2)
    expect(clases[0].min).toBe(0)
    expect(clases[clases.length - 1].max).toBeNull()
  })

  it("el color es gris para sin cobertura y un step por clase para el resto", () => {
    const clases = construirClases(JURISDICCIONES, "gasto")
    const expresion = expresionColor(clases) as unknown[]
    expect(expresion[0]).toBe("case")
    expect(JSON.stringify(expresion)).toContain('#3a3a37')
    expect(JSON.stringify(expresion)).toContain('"step"')
  })
})
