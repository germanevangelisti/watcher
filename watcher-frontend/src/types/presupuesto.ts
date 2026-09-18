export interface Programa {
  id: number;
  ejercicio: number;
  organismo: string;
  programa: string;
  subprograma?: string;
  partida_presupuestaria: string;
  descripcion: string;
  monto_inicial: number;
  monto_vigente: number;
  fecha_aprobacion: string;
  meta_fisica?: string;
  meta_numerica?: number;
  unidad_medida?: string;
  fuente_financiamiento?: string;
}

export interface Ejecucion {
  id: number;
  boletin_id?: number;
  presupuesto_base_id?: number;
  fecha_boletin: string;
  organismo?: string;
  beneficiario?: string;
  concepto?: string;
  monto: number | string;
  tipo_operacion?: string;
  partida_presupuestaria?: string;
  programa?: string;
  categoria_watcher?: string;
  riesgo_watcher?: string;
  etapa_gasto?: string;
  jurisdiccion?: string;
  monto_acumulado_mes?: number | string;
  monto_acumulado_trimestre?: number | string;
  monto_acumulado_anual?: number | string;
  requiere_revision?: boolean;
  is_duplicate: number;
  observaciones?: string;
}

export interface EjecucionListResponse {
  ejecuciones: Ejecucion[];
  total: number;
  total_monto: number | string;
  page: number;
  page_size: number;
}

export interface OrgResumenItem {
  organismo: string | null;
  count: number;
  monto_total: number | string;
  monto_compromiso: number | string;
  monto_ejecucion: number | string;
  monto_vigente: number | string | null;
  pct_compromiso: number | null;
  pct_ejecucion: number | null;
  sobre_compromiso: boolean;
  sobre_ejecucion: boolean;
  matched: boolean;
  /** Portion of monto_compromiso that is only a tender call (intención). */
  monto_llamado: number | string;
}

export interface MesResumenItem {
  mes: string; // "2026-02", "2026-03"
  count: number;
  monto_total: number | string;
}

export interface CoberturaResumen {
  monto_total: number | string;
  monto_con_denominador: number | string;
  monto_sin_denominador: number | string;
  count_sin_denominador: number;
  pct_sin_denominador: number;
}

export interface CoberturaTemporalResumen {
  mes_desde: string | null;
  mes_hasta: string | null;
  meses_cubiertos: number;
  meses_del_ejercicio: number;
  /** Months already elapsed with no ingestion — a real gap. */
  meses_vencidos_sin_ingesta: string[];
  /** Months of the ejercicio that have not happened yet. */
  meses_futuros: string[];
  dias_con_publicacion: number;
  dias_justificados: number;
  dias_faltantes: number;
  denominador_es_anual: boolean;
}

export interface DenominadorSinDuenoItemResumen {
  organismo: string;
  count: number;
  monto_vigente: number | string;
}

export interface DenominadorSinDuenoResumen {
  monto_total: number | string;
  monto_sin_dueno: number | string;
  monto_verificable: number | string;
  count_sin_dueno: number;
  pct_sin_dueno: number;
  por_organismo: DenominadorSinDuenoItemResumen[];
}

export interface EjecucionResumenResponse {
  total_canonical: number;
  total_duplicates: number;
  monto_canonical: number | string;
  monto_duplicates: number | string;
  monto_compromiso: number | string;
  monto_ejecucion: number | string;
  sobre_compromiso_count: number;
  cobertura: CoberturaResumen;
  cobertura_temporal: CoberturaTemporalResumen;
  denominador: DenominadorSinDuenoResumen;
  por_organismo: OrgResumenItem[];
  por_mes: MesResumenItem[];
}

export type JurisdiccionGasto = "provincial" | "municipal" | "fuera_presupuesto"
export type SerieGasto = "compromiso" | "ejecucion"

export interface EjecucionFilters {
  skip?: number;
  limit?: number;
  fecha_desde?: string;
  fecha_hasta?: string;
  organismo?: string;
  riesgo?: string;
  solo_canonicos?: boolean;
  presupuesto_base_id?: number;
  requiere_revision?: boolean;
  jurisdiccion?: JurisdiccionGasto;
  etapa_gasto?: string;
}

export interface ProgramaDetail extends Programa {
  ejecuciones: Ejecucion[];
  total_ejecutado: number;
  porcentaje_ejecucion: number;
}

export interface PresupuestoFilters {
  skip?: number;
  limit?: number;
  ejercicio?: number;
  organismo?: string;
}

export interface ProgramasListResponse {
  programas: Programa[];
  total: number;
  page: number;
  page_size: number;
}

export interface Organismo {
  organismo: string;
  total_programas: number;
  monto_inicial_total: number;
  monto_vigente_total: number;
}
