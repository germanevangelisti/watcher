/**
 * Types for Alertas (Alerts)
 */

export interface Alerta {
  id: number
  tipo_alerta: string
  nivel_severidad: "critica" | "alta" | "media" | "baja"
  organismo: string
  programa?: string | null
  titulo: string
  descripcion: string
  valor_detectado?: number | null
  valor_esperado?: number | null
  porcentaje_desvio?: number | null
  fecha_deteccion: string
  estado: "activa" | "revisada" | "descartada"
  created_at: string
  acciones_sugeridas?: Record<string, unknown> | null
}

export interface AlertasListResponse {
  alertas: Alerta[]
  total: number
  page: number
  page_size: number
}

export interface AlertasStats {
  total: number
  criticas: number
  altas: number
  medias: number
  bajas: number
  activas: number
  revisadas: number
  por_tipo: Record<string, number>
  por_organismo: Record<string, number>
}

export interface AlertaUpdate {
  estado?: "activa" | "revisada" | "descartada"
  observaciones_revision?: string
}

export interface AlertasFilters {
  nivel_severidad?: string
  tipo_alerta?: string
  organismo?: string
  estado?: string
}
