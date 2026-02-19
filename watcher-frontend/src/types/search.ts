// Tipos para búsqueda semántica y grafo de conocimiento

export interface SearchResult {
  chunk_id: string;
  text: string;
  score: number;
  file_name?: string;
  page_numbers?: number[];
  metadata: {
    document_id?: string;
    boletin_id?: number;
    filename?: string;
    date?: string;
    section?: string;
    section_type?: string;
    jurisdiccion_id?: string;
    chunk_id?: string;
    chunk_index?: number;
    [key: string]: unknown;
  };
  highlight?: string;
  // Legacy fields for backward compatibility
  document?: string;
  distance?: number;
}

// Actualizado para alinear con backend UnifiedSearchRequest
export interface SearchRequest {
  query: string;
  top_k?: number; // n_results renombrado a top_k
  filters?: {
    year?: string;
    month?: string;
    section?: string;
    jurisdiccion_id?: number;
  };
  technique?: 'semantic' | 'keyword' | 'hybrid'; // Nueva: técnica de búsqueda
  rerank?: boolean; // Nueva: aplicar re-ranking
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total_results: number;
  execution_time_ms: number;
  technique?: string; // Técnica usada (semantic/keyword/hybrid)
  reranked?: boolean; // Si se aplicó re-ranking
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
    metadata: Record<string, unknown>;
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
