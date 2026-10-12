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

export interface PriceReference {
  source: string
  description: string
  unit_price: number
  observed_on: string
  url: string | null
  quantity: number | null
  unit: string | null
  kind: "interna" | "externa"
}

export interface SourceStatus {
  fuente: string
  disponible: boolean
  referencias: number
  motivo: string | null
}

export interface AnalisisPrecio {
  acto: Observable
  extraccion: {
    item: string
    cantidad: number | null
    unidad: string | null
    monto_total: number | null
    metodo: "llm" | "regex"
  }
  precio_unitario: number | null
  comparacion: {
    clasificacion: Clasificacion
    motivo: string | null
    mediana: number | null
    desvio: number | null
    n_referencias: number
  }
  umbrales: { observable: number; alerta: number; min_references: number }
  fuentes: SourceStatus[]
  referencias: PriceReference[]
  proveedor_llm: string | null
  aviso: string
  analizado_en?: string | null
}
