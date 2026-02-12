import axios from 'axios';

const API_URL = 'http://localhost:8001/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Watcher endpoints
export async function analyzeText(text: string) {
  const response = await api.post('/watcher/analyze/text/', { text });
  return response.data;
}

export async function analyzeFile(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/watcher/analyze/file/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
}

// Boletines endpoints
export async function importBoletines(sourceDir: string) {
  const response = await api.post('/boletines/import/', { source_dir: sourceDir });
  return response.data;
}

export async function getBoletinesStatus() {
  const response = await api.get('/boletines/status/');
  return response.data;
}

export async function processBoletin(filename: string) {
  const response = await api.post(`/boletines/${filename}/process`);
  return response.data;
}

export async function processBatch(filenames: string[]) {
  const response = await api.post('/boletines/batch/process', { filenames });
  return response.data;
}

// Batch processing endpoints
interface BatchProcessRequest {
  source_dir: string;
  batch_size?: number;
}

export async function processDirectory(sourceDir: string, batchSize: number = 5) {
  const request: BatchProcessRequest = {
    source_dir: sourceDir,
    batch_size: batchSize
  };
  
  const response = await api.post('/batch/process/', request);
  return response.data;
}

export async function getBatchStats() {
  const response = await api.get('/batch/stats/');
  return response.data;
}

// Monthly statistics
export async function getMonthlyStats() {
  const response = await api.get('/boletines/monthly-stats/');
  return response.data;
}

// Get boletín info with red flags
export async function getBoletinInfo(filename: string) {
  const response = await api.get(`/boletines/${filename}/info`);
  return response.data;
}

// Get red flags for a document
export async function getDocumentRedFlags(documentId: string) {
  try {
    const response = await api.get(`/redflags/${documentId}`);
    return response.data;
  } catch (error) {
    console.error('Error getting red flags:', error);
    return { red_flags: [], summary: { total: 0, critical: 0, high: 0 } };
  }
}

// Alertas endpoints
import type { 
  AlertasFilters, 
  AlertasListResponse, 
  AlertasStats, 
  Alerta,
  AlertaUpdate 
} from '../types/alertas';

export async function getAlertas(filters?: AlertasFilters): Promise<AlertasListResponse> {
  const response = await api.get('/alertas/', { params: filters });
  return response.data;
}

export async function getAlertaById(id: number): Promise<Alerta> {
  const response = await api.get(`/alertas/${id}`);
  return response.data;
}

export async function getAlertasStats(): Promise<AlertasStats> {
  const response = await api.get('/alertas/stats/');
  return response.data;
}

export async function updateAlertaEstado(id: number, update: AlertaUpdate): Promise<Alerta> {
  const response = await api.patch(`/alertas/${id}/estado`, update);
  return response.data;
}

// Actos Administrativos endpoints
import type { 
  ActosFilters, 
  ActosListResponse, 
  ActoDetail, 
  Vinculo 
} from '../types/actos';

export async function getActos(filters?: ActosFilters): Promise<ActosListResponse> {
  const response = await api.get('/actos/', { params: filters });
  return response.data;
}

export async function getActoById(id: number): Promise<ActoDetail> {
  const response = await api.get(`/actos/${id}`);
  return response.data;
}

export async function getVinculosByActo(actoId: number): Promise<Vinculo[]> {
  const response = await api.get(`/actos/${actoId}/vinculos`);
  return response.data;
}

// Presupuesto endpoints
import type { 
  PresupuestoFilters, 
  ProgramasListResponse, 
  ProgramaDetail, 
  Ejecucion,
  Organismo 
} from '../types/presupuesto';

export async function getProgramas(filters?: PresupuestoFilters): Promise<ProgramasListResponse> {
  const response = await api.get('/presupuesto/programas/', { params: filters });
  return response.data;
}

export async function getProgramaById(id: number): Promise<ProgramaDetail> {
  const response = await api.get(`/presupuesto/programas/${id}`);
  return response.data;
}

export async function getEjecucionByPrograma(programaId: number): Promise<Ejecucion[]> {
  const response = await api.get(`/presupuesto/programas/${programaId}/ejecucion`);
  return response.data;
}

export async function getOrganismos(ejercicio?: number): Promise<Organismo[]> {
  const response = await api.get('/presupuesto/organismos/', { 
    params: ejercicio ? { ejercicio } : undefined 
  });
  return response.data;
}

// Métricas endpoints
import type { 
  MetricasGenerales, 
  MetricasOrganismo, 
  DistribucionRiesgo 
} from '../types/metricas';

export async function getMetricasGenerales(): Promise<MetricasGenerales> {
  const response = await api.get('/metricas/generales');
  return response.data;
}

export async function getMetricasByOrganismo(organismo: string): Promise<MetricasOrganismo> {
  const response = await api.get(`/metricas/por-organismo/${encodeURIComponent(organismo)}`);
  return response.data;
}

export async function getDistribucionRiesgo(): Promise<DistribucionRiesgo> {
  const response = await api.get('/metricas/riesgo');
  return response.data;
}

// Dashboard with real DS Lab data
export async function getDashboardStats() {
  const response = await api.get('/dashboard/stats');
  return response.data;
}

export async function getRecentRedFlags(limit: number = 20, severity?: string) {
  const params = new URLSearchParams();
  params.append('limit', limit.toString());
  if (severity) {
    params.append('severity', severity);
  }
  const response = await api.get(`/dashboard/red-flags/recent?${params.toString()}`);
  return response.data;
}

export async function getAnalysisTimeline() {
  const response = await api.get('/dashboard/timeline');
  return response.data;
}

// Búsqueda Semántica endpoints
import type { SearchRequest, SearchResponse } from '../types/search';

export async function searchEmbeddings(request: SearchRequest): Promise<SearchResponse> {
  const response = await api.post('/search/semantic', request);
  return response.data;
}

export async function getDocumentText(filename: string): Promise<{ filename: string; content: string }> {
  const response = await api.get(`/documentos/text/${encodeURIComponent(filename)}`);
  return response.data;
}

// Entidades y Grafo de Conocimiento endpoints
import type { 
  EntityNode, 
  EntityRelation, 
  EntityTimeline, 
  GraphData, 
  PatternDetection,
  EntityHistoryAnalysis 
} from '../types/search';

export async function getEntidades(params?: {
  tipo?: string;
  limit?: number;
  offset?: number;
  busqueda?: string;
}): Promise<{ entidades: EntityNode[]; total: number }> {
  const response = await api.get('/entidades/', { params });
  return response.data;
}

export async function getEntidadById(entidadId: string): Promise<EntityNode> {
  const response = await api.get(`/entidades/${entidadId}`);
  return response.data;
}

export async function getEntityTimeline(entidadId: string): Promise<EntityTimeline> {
  const response = await api.get(`/entidades/${entidadId}/timeline`);
  return response.data;
}

export async function getEntityRelations(entidadId: string): Promise<EntityRelation[]> {
  const response = await api.get(`/entidades/${entidadId}/relaciones`);
  return response.data;
}

export async function getEntityHistory(entidadId: string): Promise<EntityHistoryAnalysis> {
  const response = await api.get(`/entidades/${entidadId}/history`);
  return response.data;
}

export async function getKnowledgeGraph(params?: {
  max_nodes?: number;
  min_mentions?: number;
  entity_types?: string[];
}): Promise<GraphData> {
  const response = await api.get('/entidades/graph', { params });
  return response.data;
}

export async function detectPatterns(params?: {
  pattern_types?: string[];
  min_severity?: string;
  limit?: number;
}): Promise<PatternDetection[]> {
  const response = await api.get('/entidades/patterns', { params });
  return response.data;
}

// Compliance endpoints
export async function getComplianceScorecard(jurisdiccionId?: number) {
  const params = jurisdiccionId ? { jurisdiccion_id: jurisdiccionId } : {};
  const response = await api.get('/compliance/scorecard', { params });
  return response.data;
}

export async function getComplianceChecks(params?: {
  active_only?: boolean;
  priority?: string;
  category?: string;
}) {
  const response = await api.get('/compliance/checks', { params });
  return response.data;
}

export async function getComplianceCheckById(checkId: number) {
  const response = await api.get(`/compliance/checks/${checkId}`);
  return response.data;
}

export async function getCheckResults(params?: {
  check_id?: number;
  jurisdiccion_id?: number;
  status?: string;
  limit?: number;
}) {
  const response = await api.get('/compliance/results', { params });
  return response.data;
}

export async function getCheckResultById(resultId: number) {
  const response = await api.get(`/compliance/results/${resultId}`);
  return response.data;
}

export async function getCheckEvidence(resultId: number) {
  const response = await api.get(`/compliance/results/${resultId}/evidence`);
  return response.data;
}

export async function syncComplianceChecks() {
  const response = await api.post('/compliance/sync');
  return response.data;
}

export async function executeComplianceChecks(params?: {
  check_codes?: string[];
  jurisdiccion_id?: number;
}) {
  const response = await api.post('/compliance/execute', null, { params });
  return response.data;
}

export async function getComplianceStats(jurisdiccionId?: number) {
  const params = jurisdiccionId ? { jurisdiccion_id: jurisdiccionId } : {};
  const response = await api.get('/compliance/stats', { params });
  return response.data;
}

// Document tracking endpoints
export async function syncRequiredDocuments() {
  const response = await api.post('/compliance/documents/sync');
  return response.data;
}

export async function getRequiredDocuments(params?: {
  jurisdiccion_id?: number;
  status?: string;
  document_type?: string;
}) {
  const response = await api.get('/compliance/documents', { params });
  return response.data;
}

export async function getDocumentsOverview() {
  const response = await api.get('/compliance/documents/overview');
  return response.data;
}

export async function getJurisdictionDocuments(jurisdiccionId: number) {
  const response = await api.get(`/compliance/documents/jurisdiction/${jurisdiccionId}`);
  return response.data;
}

export async function markDocumentDownloaded(documentId: number, localPath: string, fileSizeBytes: number) {
  const response = await api.patch(`/compliance/documents/${documentId}/mark-downloaded`, null, {
    params: { local_path: localPath, file_size_bytes: fileSizeBytes }
  });
  return response.data;
}

export async function markDocumentProcessed(documentId: number, data: {
  indexed_in_rag?: boolean;
  embedding_model?: string;
  num_chunks?: number;
  metadata?: any;
}) {
  const response = await api.patch(`/compliance/documents/${documentId}/mark-processed`, data);
  return response.data;
}

export async function updateDocumentUrl(documentId: number, expectedUrl: string) {
  const response = await api.patch(`/compliance/documents/${documentId}/update-url`, null, {
    params: { expected_url: expectedUrl }
  });
  return response.data;
}

export async function uploadDocumentFile(documentId: number, file: File) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post(`/compliance/documents/${documentId}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
}

// Document processing pipeline
export async function extractDocumentText(documentId: number) {
  const response = await api.post(`/compliance/documents/${documentId}/extract-text`, null, {
    timeout: 120000 // 2 minutos
  });
  return response.data;
}

export async function indexDocumentEmbeddings(documentId: number) {
  const response = await api.post(`/compliance/documents/${documentId}/index-embeddings`, null, {
    timeout: 300000 // 5 minutos para embeddings (proceso pesado)
  });
  return response.data;
}

export async function getDocumentProcessingStatus(documentId: number) {
  const response = await api.get(`/compliance/documents/${documentId}/processing-status`);
  return response.data;
}