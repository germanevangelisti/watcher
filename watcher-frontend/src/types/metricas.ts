export interface MetricasGenerales {
  // Presupuestarias
  total_programas: number;
  monto_total_inicial: number;
  monto_total_vigente: number;
  monto_total_ejecutado: number;
  porcentaje_ejecucion_global: number;
  
  // Actos
  total_actos: number;
  actos_alto_riesgo: number;
  actos_medio_riesgo: number;
  actos_bajo_riesgo: number;
  
  // Alertas
  total_alertas: number;
  alertas_criticas: number;
  alertas_altas: number;
  
  // Vinculación
  total_vinculos: number;
  tasa_vinculacion: number;
  
  // Top 5
  top_organismos_presupuesto: Array<{
    organismo: string;
    monto: number;
  }>;
  top_organismos_riesgo: Array<{
    organismo: string;
    actos_alto_riesgo: number;
  }>;
}

export interface MetricasOrganismo {
  organismo: string;
  total_programas: number;
  monto_inicial: number;
  monto_vigente: number;
  monto_ejecutado: number;
  porcentaje_ejecucion: number;
  total_actos: number;
  actos_alto_riesgo: number;
  total_alertas: number;
  alertas_criticas: number;
}

export interface DistribucionRiesgo {
  por_nivel: Record<string, number>;
  por_tipo_acto: Record<string, Record<string, number>>;
  por_organismo: Record<string, Record<string, number>>;
  monto_por_nivel: Record<string, number>;
}

