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
  fecha_boletin: string;
  organismo: string;
  beneficiario: string;
  concepto: string;
  monto: number;
  tipo_operacion: string;
  monto_acumulado_mes?: number;
  monto_acumulado_anual?: number;
  categoria_watcher: string;
  riesgo_watcher: string;
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

