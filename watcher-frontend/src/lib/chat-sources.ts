/**
 * Fuentes de una respuesta del chat: las `data_used` que devuelve el backend.
 *
 * El backend manda **claves estructuradas** (`ejecucion_resumen`, `finalidades`, …),
 * no citas redactadas. Eso es deliberado: la fuente se declara desde el dato que
 * realmente se consultó, y nunca desde una URL que el modelo haya podido inventar.
 * Acá sólo se traducen esas claves a etiquetas legibles.
 */

export interface DataSource {
  /** Clave cruda del backend (`data_used`). */
  key: string
  /** Etiqueta humana para la burbuja. */
  label: string
}

const SOURCE_LABELS: Record<string, string> = {
  ejecucion_resumen: "Ejecución / resumen",
  organismo_desglose: "Desglose por organismo",
  actos: "Actos individuales",
  organismos: "Organismos",
  finalidades: "Finalidades",
  statistics: "Estadísticas generales",
  top_risk: "Documentos de alto riesgo",
  red_flag_distribution: "Distribución de red flags",
  red_flags: "Red flags",
  trends: "Tendencias",
  entities: "Entidades / beneficiarios",
  // Se llamó `semantic_context` y decía "Búsqueda semántica": los fragmentos son
  // el resultado de `hybrid_search` (keyword + semántica fusionadas), y en una
  // máquina donde los embeddings locales no cargan la única mitad que corre es la
  // de keyword. El chip afirmaba una búsqueda que no había ocurrido.
  corpus_boletines: "Boletines oficiales",
}

/**
 * Etiqueta de una clave de `data_used`. Una clave desconocida no se descarta ni
 * se disfraza: se muestra tal cual, con los guiones bajos convertidos en espacios
 * (el backend puede agregar una tool nueva antes que este mapa).
 */
export function sourceLabel(key: string): string {
  return SOURCE_LABELS[key] ?? key.replace(/_/g, " ")
}

/**
 * Normaliza `data_used` a la lista de fuentes a mostrar.
 *
 * Devuelve `[]` —nunca `null`— cuando no hay dato: quien decide qué hacer con la
 * ausencia es la UI. Se deduplica conservando el orden de llegada, que es el orden
 * en que el agente consultó cada fuente.
 */
export function chatSources(dataUsed?: string[] | null): DataSource[] {
  if (!dataUsed?.length) return []

  const vistas = new Set<string>()
  const fuentes: DataSource[] = []
  for (const key of dataUsed) {
    if (!key || vistas.has(key)) continue
    vistas.add(key)
    fuentes.push({ key, label: sourceLabel(key) })
  }
  return fuentes
}
