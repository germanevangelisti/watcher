/** WMA1 — gasto por jurisdicción, para el mapa de Córdoba. */

export type NivelJurisdiccion = "municipal" | "comunal"

export interface JurisdiccionGasto {
  /** Código del catálogo ReFeGLo; es la clave que une las grafías del nombre. */
  codigo: string
  nombre: string
  tipo: "municipio" | "comuna"
  departamento: string | null
  nivel: NivelJurisdiccion
  poblacion_2022: number | null
  actos: number
  /** Actos republicados: no cuentan ni suman. */
  republicaciones: number
  gasto: number
  /** `null` cuando no hay actos: sin datos no es $0 por habitante. */
  gasto_per_capita: number | null
  cobertura: boolean
}

export interface NivelTotal {
  nivel: string
  actos: number
  gasto: number
}

export interface GastoPorJurisdiccionResponse {
  /** Las 427 jurisdicciones, incluidas las que no tienen actos. */
  jurisdicciones: JurisdiccionGasto[]
  por_nivel: NivelTotal[]
  /** Gasto municipal/comunal que el acto no asigna a ningún gobierno local. */
  sin_jurisdiccion: { actos: number; gasto: number; niveles: string[] }
  totales: { actos: number; gasto: number; con_cobertura: number; jurisdicciones: number }
  fuente: {
    catalogo: string
    poblacion: string
    limites: string
    fecha: string
    nota: string
  }
}

export type MetricaMapa = "gasto" | "per_capita" | "actos"

/** Filtro por tamaño de la jurisdicción (población del Censo 2022). */
export type TamanoJurisdiccion = "todos" | "grande" | "mediano" | "chico" | "sin_poblacion"

export interface ClaseMetrica {
  /** Límite inferior inclusive. */
  min: number
  /** Límite superior inclusive; `null` = sin techo. */
  max: number | null
  /** Cuántas jurisdicciones con cobertura caen en la clase. */
  count: number
  color: string
}

/** Lo mínimo del GeoJSON estático que usa el mapa (evita otra dependencia). */
export interface FeatureGeo {
  type: "Feature"
  properties: Record<string, unknown>
  geometry: unknown
}

export interface FeatureCollectionGeo {
  type: "FeatureCollection"
  features: FeatureGeo[]
}
