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

// ===== Ampliación B — techo por finalidad y proxy BO (en millones de ARS) =====

export interface FinalidadDetalleItem {
  clave: string;
  /** `null` para componentes que no son finalidades del clasificador (el `6`). */
  label?: string | null;
  count: number;
  monto_inicial: number | string;
  monto_vigente: number | string;
  participacion_techo_pct: number;
}

export interface FinalidadItem {
  clave: string;
  label: string;
  count: number;
  monto_inicial: number | string;
  monto_vigente: number | string;
  participacion_techo_pct: number;
  detalle: FinalidadDetalleItem[];
}

export interface HonestidadResumen {
  es_techo: boolean;
  /** Medido fila por fila: no se afirma si el corte no lo sostiene. */
  inicial_es_vigente: boolean;
  filas_inicial_distinto_vigente: number;
  es_credito_modificado: boolean;
  incluye_devengado_cge: boolean;
  /** El copy, generado de la medición de arriba. La UI lo lee, no lo inventa. */
  notas: string[];
}

export interface FinalidadesResumen {
  ejercicio: number;
  total_inicial: number | string;
  total_vigente: number | string;
  total_registros: number;
  items: FinalidadItem[];
  honestidad: HonestidadResumen;
}

export interface ProxyBoDetalleItem {
  clave: string;
  label?: string | null;
  count: number;
  monto_publicado: number | string;
  monto_techo: number | string;
  /** `null` sin techo: un 0% ahí afirmaría algo que no se midió. */
  pct_publicado_techo: number | null;
}

export interface ProxyBoItem {
  clave: string;
  label: string;
  count: number;
  monto_publicado: number | string;
  monto_techo: number | string;
  pct_publicado_techo: number | null;
  detalle: ProxyBoDetalleItem[];
}

export interface CoberturaProxyBoResumen {
  monto_total: number | string;
  monto_con_programa: number | string;
  /** Publicado que no se pudo atribuir. Se declara: no se reparte. */
  monto_sin_programa: number | string;
  count_sin_programa: number;
  pct_sin_programa: number;
  monto_atribuido_finalidad: number | string;
  monto_no_clasificado: number | string;
  fecha_desde: string | null;
  fecha_hasta: string | null;
  denominador_es_anual: boolean;
}

export interface EtapaProxyBoResumen {
  clave: string;
  label: string;
  monto: number | string;
}

export interface HonestidadProxyBoResumen {
  es_proxy_bo: boolean;
  /** Siempre `false`: lo publicado en el BO no devenga gasto. */
  es_devengado: boolean;
  es_devengado_cge: boolean;
  /** La etiqueta del numerador. La UI la muestra en vez de elegirla. */
  etiqueta_numerador: string;
  notas: string[];
}

export interface ProxyBoResumen {
  ejercicio: number;
  items: ProxyBoItem[];
  cobertura: CoberturaProxyBoResumen;
  etapas: EtapaProxyBoResumen[];
  honestidad: HonestidadProxyBoResumen;
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
