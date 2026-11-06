import { useEffect, useRef, useState } from "react"
import maplibregl, {
  type GeoJSONSource,
  type Map as MapaLibre,
  type StyleSpecification,
} from "maplibre-gl"
import "maplibre-gl/dist/maplibre-gl.css"
import {
  BORDE_SIN_COBERTURA,
  MAPA_BORDE,
  MAPA_FONDO,
  construirFeatureCollection,
  expresionColor,
  popupHtml,
} from "@/lib/mapa-gasto"
import type {
  ClaseMetrica,
  FeatureCollectionGeo,
  JurisdiccionGasto,
  MetricaMapa,
  TamanoJurisdiccion,
} from "@/types/mapa-gasto"

/** Córdoba: el encuadre del mapa no depende de tiles ni de geocoding. */
const LIMITES_CORDOBA: [[number, number], [number, number]] = [
  [-65.95, -34.95],
  [-61.6, -29.2],
]

const GEOJSON_MUNICIPIOS = "/geo/municipios-cordoba.geojson"

const ESTILO_BASE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "fondo", type: "background", paint: { "background-color": MAPA_FONDO } }],
}

export interface MapaJurisdiccionesProps {
  jurisdicciones: JurisdiccionGasto[]
  clases: ClaseMetrica[]
  metrica: MetricaMapa
  tamano: TamanoJurisdiccion
  /** Los límites se sirven estáticos: sin tiles de terceros ni claves de API. */
  geojsonUrl?: string
}

/**
 * Mapa MapLibre con los límites de municipios y comunas de Córdoba.
 *
 * No usa tiles externos: el fondo es plano y la única capa es el GeoJSON
 * simplificado que se sirve desde `public/geo`.  Click en un área abre el popup
 * con los números y el link al listado de actos de esa jurisdicción.
 */
export function MapaJurisdicciones({
  jurisdicciones,
  clases,
  metrica,
  tamano,
  geojsonUrl = GEOJSON_MUNICIPIOS,
}: MapaJurisdiccionesProps) {
  const contenedor = useRef<HTMLDivElement | null>(null)
  const mapaRef = useRef<MapaLibre | null>(null)
  const geojsonRef = useRef<FeatureCollectionGeo | null>(null)
  const jurisdiccionesRef = useRef(jurisdicciones)
  jurisdiccionesRef.current = jurisdicciones
  // Los valores iniciales del mapa se leen de refs: el efecto de montaje no debe
  // recrear el mapa cada vez que cambia un filtro.
  const metricaRef = useRef(metrica)
  metricaRef.current = metrica
  const tamanoRef = useRef(tamano)
  tamanoRef.current = tamano
  const clasesRef = useRef(clases)
  clasesRef.current = clases
  const [listo, setListo] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!contenedor.current) return
    const mapa = new maplibregl.Map({
      container: contenedor.current,
      style: ESTILO_BASE,
      bounds: LIMITES_CORDOBA,
      attributionControl: false,
      dragRotate: false,
    })
    mapaRef.current = mapa
    mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right")
    mapa.addControl(
      new maplibregl.AttributionControl({
        compact: true,
        customAttribution: "Límites: © OpenStreetMap contributors (ODbL)",
      }),
      "bottom-right",
    )

    let cancelado = false
    const alCargar = async () => {
      try {
        const respuesta = await fetch(geojsonUrl)
        if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`)
        const geojson = (await respuesta.json()) as FeatureCollectionGeo
        if (cancelado) return
        geojsonRef.current = geojson
        mapa.addSource("jurisdicciones", {
          type: "geojson",
          data: construirFeatureCollection(
            geojson,
            jurisdiccionesRef.current,
            metricaRef.current,
            tamanoRef.current,
          ),
        })
        mapa.addLayer({
          id: "jurisdicciones-fill",
          type: "fill",
          source: "jurisdicciones",
          paint: {
            "fill-color": expresionColor(clasesRef.current) as never,
            "fill-opacity": 0.9,
            "fill-outline-color": MAPA_BORDE,
          },
        })
        mapa.addLayer({
          id: "jurisdicciones-line",
          type: "line",
          source: "jurisdicciones",
          paint: { "line-color": BORDE_SIN_COBERTURA, "line-width": 0.4, "line-opacity": 0.5 },
        })
        mapa.on("click", "jurisdicciones-fill", (evento) => {
          const codigo = evento.features?.[0]?.properties?.codigo
          const jurisdiccion = jurisdiccionesRef.current.find((j) => j.codigo === String(codigo))
          if (!jurisdiccion) return
          new maplibregl.Popup({ closeButton: true, maxWidth: "320px" })
            .setLngLat(evento.lngLat)
            .setHTML(popupHtml(jurisdiccion))
            .addTo(mapa)
        })
        mapa.on("mouseenter", "jurisdicciones-fill", () => {
          mapa.getCanvas().style.cursor = "pointer"
        })
        mapa.on("mouseleave", "jurisdicciones-fill", () => {
          mapa.getCanvas().style.cursor = ""
        })
        setListo(true)
      } catch {
        if (!cancelado) {
          setError("No se pudieron cargar los límites de los municipios.")
        }
      }
    }
    mapa.on("load", alCargar)

    return () => {
      cancelado = true
      setListo(false)
      mapa.remove()
      mapaRef.current = null
    }
  }, [geojsonUrl])

  // La métrica y el filtro no recrean el mapa: se reescribe la fuente y el relleno.
  useEffect(() => {
    if (!listo || !geojsonRef.current) return
    const mapa = mapaRef.current
    if (!mapa) return
    const fuente = mapa.getSource("jurisdicciones") as GeoJSONSource | undefined
    fuente?.setData(construirFeatureCollection(geojsonRef.current, jurisdicciones, metrica, tamano))
    mapa.setPaintProperty("jurisdicciones-fill", "fill-color", expresionColor(clases) as never)
    const visibles: never = ["==", ["get", "visible"], true] as never
    mapa.setFilter("jurisdicciones-fill", visibles)
    mapa.setFilter("jurisdicciones-line", visibles)
  }, [listo, jurisdicciones, metrica, tamano, clases])

  return (
    <div
      data-testid="mapa-jurisdicciones"
      className="relative h-[520px] w-full overflow-hidden rounded-md border border-border"
    >
      <div ref={contenedor} className="h-full w-full" />
      {error && (
        <p data-testid="mapa-error" className="absolute inset-x-0 top-0 bg-destructive/90 p-2 text-sm">
          {error}
        </p>
      )}
    </div>
  )
}
