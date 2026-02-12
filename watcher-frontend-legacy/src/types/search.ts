// Tipos para búsqueda semántica y grafo de conocimiento

export interface SearchResult {
  document: string;
  metadata: {
    document_id: string;
    filename: string;
    date: string;
    section: string;
    jurisdiccion_id: string;
    chunk_id: string;
  };
  distance: number;
  score: number;
}

export interface SearchRequest {
  query: string;
  n_results?: number;
  filters?: {
    year?: string;
    month?: string;
    section?: string;
    jurisdiccion_id?: number;
  };
  model?: string;  // Modelo de búsqueda
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total_results: number;
  execution_time_ms: number;
}

// Tipos para Grafo de Conocimiento

export interface EntityNode {
  id: string;
  tipo: 'persona' | 'organismo' | 'empresa' | 'contrato' | 'monto';
  nombre: string;
  nombre_normalizado: string;
  primera_aparicion: string;
  ultima_aparicion: string;
  total_menciones: number;
}

export interface EntityRelation {
  id: number;
  entidad_origen_id: string;
  entidad_destino_id: string;
  tipo_relacion: 'contrata' | 'designa' | 'adjudica' | 'menciona';
  confianza: number;
  primera_deteccion: string;
  total_ocurrencias: number;
}

export interface EntityTimeline {
  entidad_id: string;
  entidad_nombre: string;
  eventos: Array<{
    fecha: string;
    documento_id: number;
    boletin_filename: string;
    contexto: string;
    tipo_evento: string;
  }>;
}

export interface GraphData {
  nodes: Array<{
    id: string;
    label: string;
    type: string;
    mentions: number;
    group: number;
  }>;
  links: Array<{
    source: string;
    target: string;
    type: string;
    weight: number;
    confidence: number;
  }>;
}

export interface PatternDetection {
  pattern_name: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  entities: string[];
  detecciones: Array<{
    entidad_id: string;
    entidad_nombre: string;
    fecha: string;
    documento_id: number;
    metadata: Record<string, any>;
  }>;
  estadisticas: {
    total_casos: number;
    periodo_inicio: string;
    periodo_fin: string;
  };
}

export interface EntityHistoryAnalysis {
  entidad: EntityNode;
  timeline: EntityTimeline;
  relaciones: Array<{
    relacion: EntityRelation;
    entidad_relacionada: EntityNode;
  }>;
  patrones_sospechosos: PatternDetection[];
  estadisticas: {
    total_documentos: number;
    total_relaciones: number;
    periodo_actividad: {
      inicio: string;
      fin: string;
    };
    frecuencia_mensual: Record<string, number>;
  };
}
