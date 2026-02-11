export interface Alerta {
  id: number;
  tipo_alerta: string;
  nivel_severidad: 'CRITICA' | 'ALTA' | 'MEDIA' | 'BAJA';
  organismo: string;
  programa?: string;
  titulo: string;
  descripcion: string;
  valor_detectado?: number;
  valor_esperado?: number;
  porcentaje_desvio?: number;
  fecha_deteccion: string;
  estado: 'activa' | 'revisada' | 'resuelta' | 'falsa';
  created_at: string;
  acciones_sugeridas?: Record<string, any>;
}

export interface AlertasFilters {
  skip?: number;
  limit?: number;
  nivel_severidad?: string;
  tipo_alerta?: string;
  organismo?: string;
  estado?: string;
}

export interface AlertasListResponse {
  alertas: Alerta[];
  total: number;
  page: number;
  page_size: number;
}

export interface AlertasStats {
  total: number;
  criticas: number;
  altas: number;
  medias: number;
  bajas: number;
  activas: number;
  revisadas: number;
  por_tipo: Record<string, number>;
  por_organismo: Record<string, number>;
}

export interface AlertaUpdate {
  estado?: string;
  observaciones_revision?: string;
}
