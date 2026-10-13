export interface Observable {
  id: number
  fecha: string | null
  organismo: string | null
  concepto: string | null
  monto: number | null
  tipo_operacion: string | null
  etapa_gasto: string | null
  boletin_id: number | null
  boletin_url: string | null
  motivo: string
  ultima_clasificacion?: Clasificacion | null
}

export interface ObservablesResponse {
  total: number
  items: Observable[]
}

export type Clasificacion = "dentro_de_rango" | "observable" | "alerta" | "sin_datos_suficientes"

/** M8 — figura/procedimiento por el que se mueve el dinero (`etapa_gasto` dice el momento). */
export type TipoGasto =
  | "licitacion"
  | "concurso_precios"
  | "subasta_electronica"
  | "compra_directa"
  | "contratacion"
  | "subsidio_transferencia"
  | "otro"
  | "no_es_gasto"

/** M8 — qué se compra o se hace. Eje aparte de `tipo_gasto`: un acto puede ser
 * «licitación · obra» sin tener que elegir entre las dos cosas. */
export type Objeto = "obra" | "bien" | "servicio" | "transferencia" | "otro" | "no_aplica"

/** M8 — nivel de gobierno, eje distinto de `jurisdiccion_gasto`. */
export type Nivel = "provincial" | "municipal" | "comunal" | "nacional" | "desconocido"

export interface GastoDetectado {
  analisis_id: number
  /** Presente sólo si el acto está en el ledger; sin él no hay análisis de precio. */
  ejecucion_id: number | null
  fecha: string | null
  boletin_id: number | null
  boletin_url: string | null
  organismo: string | null
  municipio: string | null
  nivel: Nivel
  tipo_gasto: TipoGasto
  objeto: Objeto
  etapa_gasto: string | null
  /** Qué es el acto (descripción, o el fragmento si no hay). */
  concepto: string | null
  /** Por qué se clasificó así. */
  gasto_motivo: string | null
  monto: number | null
  /** Tiene figura de gasto. Distinto de `en_ledger`, que es la afirmación fuerte. */
  es_gasto_publico: boolean
  en_ledger: boolean
  /** Republicación del mismo acto: se lista, pero no suma. */
  is_duplicate_gasto: boolean
  ultima_clasificacion: Clasificacion | null
}

export interface GastoDetectadoResponse {
  total: number
  /** Suma del filtro entero, sin republicaciones. */
  suma: number
  /** Lo que `suma` dejó afuera por ser republicación. */
  republicaciones_excluidas: number
  items: GastoDetectado[]
}

export interface GastoFiltros {
  tipo?: string
  objeto?: string
  nivel?: string
  organismo?: string
  municipio?: string
  q?: string
  fecha_desde?: string
  fecha_hasta?: string
  monto_min?: string
  monto_max?: string
  solo_gasto?: boolean
  limit?: number
  offset?: number
}

export interface PriceReference {
  source: string
  description: string
  unit_price: number
  observed_on: string
  url: string | null
  quantity: number | null
  unit: string | null
  kind: "interna" | "externa" | "oficial"
  process_id?: string | null
}

export interface Renglon {
  numero: number | null
  descripcion: string
  cantidad: number | null
  precio_referencia: number | null
  presupuesto: number | null
}

export interface ProcesoCompras {
  nro: string
  tipo: string
  servicio: string
  objeto: string
  estado: string
  presupuesto_total: number | null
  fecha_limite: string | null
  documento: string | null
  origen: string | null
  url: string
  motivo: string | null
}

export interface SourceStatus {
  fuente: string
  disponible: boolean
  referencias: number
  motivo: string | null
}

export interface Comparacion {
  clasificacion: Clasificacion
  motivo: string | null
  mediana: number | null
  desvio: number | null
  n_referencias: number
}

export interface RenglonAnalisis {
  numero: number | null
  item: string
  cantidad: number | null
  unidad: string
  precio_unitario: number | null
  origen_precio: string | null
  comparacion: Comparacion
  fuentes: SourceStatus[]
  referencias: PriceReference[]
}

export interface AgregadoRenglones {
  renglones: number
  por_clasificacion: Partial<Record<Clasificacion, number>>
  monto_total_acto: number | null
  estimado_mercado: number | null
  desvio: number | null
  clasificacion: Clasificacion
  motivo: string | null
  nota: string
}

export interface AnalisisPrecio {
  acto: Observable
  extraccion: {
    item: string
    cantidad: number | null
    unidad: string | null
    monto_total: number | null
    metodo: "llm" | "regex"
    fuente_cantidad?: string | null
    renglones?: Renglon[]
    proceso?: ProcesoCompras | null
  }
  precio_unitario: number | null
  comparacion: Comparacion
  renglones_analisis?: RenglonAnalisis[]
  agregado?: AgregadoRenglones | null
  umbrales: { observable: number; alerta: number; min_references: number }
  fuentes: SourceStatus[]
  referencias: PriceReference[]
  proveedor_llm: string | null
  aviso: string
  analizado_en?: string | null
}
