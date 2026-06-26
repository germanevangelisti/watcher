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
  monto: number;
  tipo_operacion?: string;
  partida_presupuestaria?: string;
  programa?: string;
  categoria_watcher?: string;
  riesgo_watcher?: string;
  monto_acumulado_mes?: number;
  monto_acumulado_trimestre?: number;
  monto_acumulado_anual?: number;
  requiere_revision?: boolean;
  is_duplicate: number;
  observaciones?: string;
}

export interface EjecucionListResponse {
  ejecuciones: Ejecucion[];
  total: number;
  total_monto: number;
  page: number;
  page_size: number;
}

export interface OrgResumenItem {
  organismo: string | null;
  count: number;
  monto_total: number;
}

export interface MesResumenItem {
  mes: string; // "2026-02", "2026-03"
  count: number;
  monto_total: number;
}

export interface EjecucionResumenResponse {
  total_canonical: number;
  total_duplicates: number;
  monto_canonical: number;
  monto_duplicates: number;
  por_organismo: OrgResumenItem[];
  por_mes: MesResumenItem[];
}

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
