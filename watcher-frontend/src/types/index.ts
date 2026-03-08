// Export all types from a central location
export * from './search'
export * from './boletines'
export * from './actos'
export * from './alertas'
export * from './metricas'
export * from './presupuesto'

// ─── Calendario de Boletines ─────────────────────────────────────────────────

export interface SeccionDia {
  numero: string
  nombre: string
  status: "completed" | "pending" | "processing" | "error" | "not_found"
  boletin_id: number | null
}

export interface DiaBoletin {
  es_habil: boolean
  secciones: SeccionDia[]
}

export interface JurisdiccionCalendar {
  id: number
  nombre: string
  dias: Record<string, DiaBoletin>  // key = "YYYYMMDD"
}

export interface CalendarResponse {
  year: number
  month: number
  jurisdicciones: JurisdiccionCalendar[]
}

// ─── Fuentes de Datos ─────────────────────────────────────────────────────────

export type TipoFuenteDato = "boletin_diario" | "presupuesto_anual" | "ejecucion_trimestral"

export interface FuenteDato {
  id: number
  jurisdiccion_id: number
  jurisdiccion_nombre: string | null
  tipo: TipoFuenteDato
  nombre: string
  url_template: string | null
  activa: boolean
  descripcion: string | null
  created_at: string | null
  updated_at: string | null
}

export interface FuenteDatoCreateRequest {
  jurisdiccion_id: number
  tipo: TipoFuenteDato
  nombre: string
  url_template?: string
  activa?: boolean
  descripcion?: string
}

export interface FuenteDatoUpdateRequest {
  nombre?: string
  url_template?: string
  activa?: boolean
  descripcion?: string
}

// ─── Common types ─────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string;
  status?: number;
}

export interface PaginationParams {
  skip?: number;
  limit?: number;
}

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}
