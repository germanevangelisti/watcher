import { formatArs } from "@/lib/precio-mercado-format"
import type {
  ClaseMetrica,
  FeatureCollectionGeo,
  JurisdiccionGasto,
  MetricaMapa,
  TamanoJurisdiccion,
} from "@/types/mapa-gasto"

/**
 * Escala secuencial de un solo tono (azul), oscura→clara: en un mapa sobre fondo
 * oscuro, más gasto se lee como más luz.  La clase más baja se acerca al fondo a
 * propósito; la leyenda rotula cada rango y su cantidad, así que el color no es
 * el único canal.  Sin cobertura va en gris, nunca en el azul más bajo.
 */
export const RAMPAS_METRICA: Record<MetricaMapa, string[]> = {
  gasto: ["#1c5cab", "#2a78d6", "#5598e7", "#86b6ef", "#b7d3f6"],
  per_capita: ["#1c5cab", "#2a78d6", "#5598e7", "#86b6ef", "#b7d3f6"],
  actos: ["#1c5cab", "#2a78d6", "#5598e7", "#86b6ef", "#b7d3f6"],
}

export const COLOR_SIN_COBERTURA = "#3a3a37"
export const BORDE_SIN_COBERTURA = "#6b6a65"
export const MAPA_FONDO = "#020817"
export const MAPA_BORDE = "#38414f"

export const METRICA_LABEL: Record<MetricaMapa, string> = {
  gasto: "Gasto detectado",
  per_capita: "Gasto per cápita",
  actos: "Cantidad de actos",
}

export const TAMANO_LABEL: Record<TamanoJurisdiccion, string> = {
  todos: "Todos los tamaños",
  grande: "Grandes (≥ 50.000 hab.)",
  mediano: "Medianos (10.000–50.000)",
  chico: "Chicos (< 10.000 hab.)",
  sin_poblacion: "Sin dato de población",
}

const compacto = new Intl.NumberFormat("es-AR", {
  style: "currency",
  currency: "ARS",
  notation: "compact",
  maximumFractionDigits: 1,
})

export function valorMetrica(j: JurisdiccionGasto, metrica: MetricaMapa): number {
  if (metrica === "actos") return j.actos
  if (metrica === "per_capita") return j.gasto_per_capita ?? 0
  return j.gasto
}

export function formatearMetrica(valor: number | null, metrica: MetricaMapa): string {
  if (valor == null) return "sin datos"
  if (metrica === "actos") return `${valor} ${valor === 1 ? "acto" : "actos"}`
  return formatArs(valor)
}

export function formatearMetricaCompacta(valor: number, metrica: MetricaMapa): string {
  if (metrica === "actos") return String(valor)
  return compacto.format(valor)
}

/** Rango de una clase, para la leyenda. `null` en el techo = sin techo. */
export function etiquetaClase(clase: ClaseMetrica, metrica: MetricaMapa): string {
  const desde = formatearMetricaCompacta(clase.min, metrica)
  if (clase.max == null) return `≥ ${desde}`
  if (clase.min >= clase.max) return desde
  return `${desde} – ${formatearMetricaCompacta(clase.max, metrica)}`
}

export function filtrarPorTamano(j: JurisdiccionGasto, tamano: TamanoJurisdiccion): boolean {
  const poblacion = j.poblacion_2022
  switch (tamano) {
    case "todos":
      return true
    case "sin_poblacion":
      return poblacion == null
    case "grande":
      return poblacion != null && poblacion >= 50_000
    case "mediano":
      return poblacion != null && poblacion >= 10_000 && poblacion < 50_000
    case "chico":
      return poblacion != null && poblacion < 10_000
  }
}

export function jurisdiccionesVisibles(
  jurisdicciones: JurisdiccionGasto[],
  tamano: TamanoJurisdiccion,
): JurisdiccionGasto[] {
  return jurisdicciones.filter((j) => filtrarPorTamano(j, tamano))
}

/**
 * Clases por cuantiles sobre las jurisdicciones **con cobertura**: los colores se
 * reparten entre las que tienen datos, no entre las 427.  Con pocos valores
 * distintos las clases se colapsan (no se inventan rangos vacíos).
 */
export function construirClases(
  jurisdicciones: JurisdiccionGasto[],
  metrica: MetricaMapa,
  colores: string[] = RAMPAS_METRICA[metrica],
): ClaseMetrica[] {
  const valores = jurisdicciones
    .filter((j) => j.cobertura)
    .map((j) => valorMetrica(j, metrica))
    .filter((v) => v > 0)
    .sort((a, b) => a - b)
  if (valores.length === 0) return []

  const cortes: number[] = []
  for (let i = 1; i < colores.length; i += 1) {
    const indice = Math.min(valores.length - 1, Math.floor((i / colores.length) * valores.length))
    const corte = valores[indice]
    if (cortes.length === 0 || corte > cortes[cortes.length - 1]) cortes.push(corte)
  }

  const clases: ClaseMetrica[] = []
  let inferior = 0
  cortes.forEach((corte, i) => {
    clases.push({ min: inferior, max: corte, count: 0, color: colorDeClase(i, cortes.length + 1, colores) })
    inferior = corte
  })
  clases.push({
    min: inferior,
    max: null,
    count: 0,
    color: colorDeClase(cortes.length, cortes.length + 1, colores),
  })

  for (const valor of valores) {
    const clase = clases.find((c) => c.max == null || valor <= c.max) ?? clases[clases.length - 1]
    clase.count += 1
  }
  return clases
}

/** Reparte los pasos de la rampa entre las clases que sobrevivieron. */
function colorDeClase(indice: number, total: number, colores: string[]): string {
  if (total <= 1) return colores[Math.floor(colores.length / 2)]
  const paso = Math.round((indice * (colores.length - 1)) / (total - 1))
  return colores[paso]
}

export function colorDe(j: JurisdiccionGasto, clases: ClaseMetrica[], metrica: MetricaMapa): string {
  if (!j.cobertura) return COLOR_SIN_COBERTURA
  const valor = valorMetrica(j, metrica)
  const clase = clases.find((c) => c.max == null || valor <= c.max)
  return clase?.color ?? COLOR_SIN_COBERTURA
}

export function urlListado(j: JurisdiccionGasto): string {
  const query = new URLSearchParams({
    municipio: j.nombre,
    municipio_codigo: j.codigo,
  })
  return `/analisis/precio-mercado?${query.toString()}`
}

/**
 * Expresión de MapLibre para pintar el relleno: gris si la jurisdicción no tiene
 * datos, y si no un `step` con los cortes de las clases.  Se calcula una vez por
 * cambio de métrica, no por feature.
 */
export function expresionColor(clases: ClaseMetrica[]): unknown[] | string {
  if (clases.length === 0) return COLOR_SIN_COBERTURA
  const paso: (string | number | string[])[] = ["step", ["get", "valor"], clases[0].color]
  for (const clase of clases.slice(1)) {
    paso.push(clase.min, clase.color)
  }
  return ["case", ["==", ["get", "cobertura"], false], COLOR_SIN_COBERTURA, paso]
}

/**
 * Une el GeoJSON estático con la respuesta del API: cada polígono gana `valor`
 * (métrica elegida) y `visible` (filtro de tamaño).  Las jurisdicciones sin actos
 * igual entran, con `cobertura: false`, para que se pinten en gris.
 */
export function construirFeatureCollection(
  geojson: FeatureCollectionGeo,
  jurisdicciones: JurisdiccionGasto[],
  metrica: MetricaMapa,
  tamano: TamanoJurisdiccion,
): FeatureCollectionGeo {
  const porCodigo = new Map(jurisdicciones.map((j) => [j.codigo, j]))
  return {
    ...geojson,
    features: geojson.features.map((feature) => {
      const codigo = String(feature.properties.codigo ?? "")
      const jurisdiccion = porCodigo.get(codigo)
      return {
        ...feature,
        properties: {
          ...feature.properties,
          cobertura: jurisdiccion?.cobertura ?? false,
          valor: jurisdiccion ? valorMetrica(jurisdiccion, metrica) : 0,
          visible: jurisdiccion ? filtrarPorTamano(jurisdiccion, tamano) : false,
        },
      }
    }),
  }
}

function escaparHtml(texto: string): string {
  return texto
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
}

/** Contenido del popup: los números y el link al listado, sin adjetivos. */
export function popupHtml(j: JurisdiccionGasto): string {
  const tipo = j.tipo === "municipio" ? "Municipio" : "Comuna"
  const perCapita = j.gasto_per_capita == null
    ? "sin datos"
    : formatArs(j.gasto_per_capita)
  const poblacion = j.poblacion_2022 == null
    ? "sin dato"
    : new Intl.NumberFormat("es-AR").format(j.poblacion_2022)
  const sinDatos = !j.cobertura
    ? `<p class="mapa-popup-sin-datos">Sin actos de gasto detectados en el corte: no es gasto cero.</p>`
    : `<dl class="mapa-popup-datos">
         <dt>Gasto detectado</dt><dd>${formatArs(j.gasto)}</dd>
         <dt>Actos</dt><dd>${j.actos}</dd>
         <dt>Per cápita</dt><dd>${perCapita}</dd>
       </dl>`
  return `<div class="mapa-popup-contenido">
    <strong>${escaparHtml(j.nombre)}</strong>
    <span class="mapa-popup-meta">${tipo}${j.departamento ? ` · Dpto. ${escaparHtml(j.departamento)}` : ""} · ${poblacion} hab. (Censo 2022)</span>
    ${sinDatos}
    <a class="mapa-popup-link" href="${urlListado(j)}">Ver los actos de ${escaparHtml(j.nombre)}</a>
  </div>`
}
