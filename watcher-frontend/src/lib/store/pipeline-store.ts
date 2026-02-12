/**
 * Pipeline Zustand store - Tracks pipeline processing state in real-time.
 * Updated via WebSocket events from the backend EventBus.
 */

import { create } from "zustand"

// =============================================================================
// Types
// =============================================================================

export interface StageHistoryEntry {
  stage: string
  timestamp: string
  details?: Record<string, unknown>
}

export interface PipelineDocumentState {
  boletinId: number
  filename: string
  stage: string
  error?: string
  updatedAt: string
}

export interface PipelineError {
  boletinId: number
  filename: string
  error: string
  stage: string
  timestamp: string
}

export interface PipelineStats {
  totalBoletines: number
  byStatus: Record<string, number>
  totalChunks: number
  totalIndexed: number
}

export interface PipelineConfigState {
  extraction: {
    extractor: string
  }
  cleaning: {
    enabled: boolean
    fix_encoding: boolean
    normalize_unicode: boolean
    normalize_whitespace: boolean
    remove_artifacts: boolean
    normalize_legal_text: boolean
  }
  chunking: {
    chunk_size: number
    chunk_overlap: number
    min_chunk_size: number
    strategy: string
  }
  enrichment: {
    enabled: boolean
    detect_section_type: boolean
    detect_amounts: boolean
    detect_tables: boolean
    extract_entities: boolean
  }
  indexing: {
    use_sqlite: boolean
    use_fts5: boolean
    use_chromadb: boolean
    embedding_model: string
  }
}

// =============================================================================
// Store Interface
// =============================================================================

interface PipelineStore {
  // State
  isProcessing: boolean
  sessionId: string | null
  progress: { current: number; total: number }
  currentFilename: string | null
  currentStage: string | null
  stageHistory: StageHistoryEntry[]
  documentStates: Record<number, PipelineDocumentState>
  errors: PipelineError[]
  stats: PipelineStats | null
  config: PipelineConfigState | null

  // Actions
  setProcessing: (sessionId: string, total: number) => void
  updateDocumentState: (boletinId: number, filename: string, stage: string) => void
  addStageToHistory: (stage: string, details?: Record<string, unknown>) => void
  setDocumentCompleted: (boletinId: number) => void
  setDocumentFailed: (boletinId: number, filename: string, error: string, stage: string) => void
  setProgress: (current: number, total: number, filename?: string, stage?: string) => void
  setCompleted: (total: number, completed: number, failed: number) => void
  setStats: (stats: PipelineStats) => void
  setConfig: (config: PipelineConfigState) => void
  reset: () => void
}

// =============================================================================
// Default Config
// =============================================================================

export const DEFAULT_PIPELINE_CONFIG: PipelineConfigState = {
  extraction: { extractor: "pdfplumber" },
  cleaning: {
    enabled: true,
    fix_encoding: true,
    normalize_unicode: true,
    normalize_whitespace: true,
    remove_artifacts: true,
    normalize_legal_text: true,
  },
  chunking: {
    chunk_size: 1000,
    chunk_overlap: 200,
    min_chunk_size: 100,
    strategy: "recursive",
  },
  enrichment: {
    enabled: true,
    detect_section_type: true,
    detect_amounts: true,
    detect_tables: true,
    extract_entities: true,
  },
  indexing: {
    use_sqlite: true,
    use_fts5: true,
    use_chromadb: true,
    embedding_model: "gemini-embedding-001",
  },
}

// =============================================================================
// Store
// =============================================================================

export const usePipelineStore = create<PipelineStore>((set) => ({
  // Initial state
  isProcessing: false,
  sessionId: null,
  progress: { current: 0, total: 0 },
  currentFilename: null,
  currentStage: null,
  stageHistory: [],
  documentStates: {},
  errors: [],
  stats: null,
  config: DEFAULT_PIPELINE_CONFIG,

  // Actions
  setProcessing: (sessionId, total) =>
    set({
      isProcessing: true,
      sessionId,
      progress: { current: 0, total },
      stageHistory: [],
      errors: [],
    }),

  updateDocumentState: (boletinId, filename, stage) =>
    set((state) => ({
      currentFilename: filename,
      currentStage: stage,
      documentStates: {
        ...state.documentStates,
        [boletinId]: {
          boletinId,
          filename,
          stage,
          updatedAt: new Date().toISOString(),
        },
      },
    })),

  addStageToHistory: (stage, details) =>
    set((state) => {
      // Avoid duplicates
      if (state.stageHistory.some((s) => s.stage === stage)) return state
      return {
        stageHistory: [
          ...state.stageHistory,
          { stage, timestamp: new Date().toISOString(), details },
        ],
      }
    }),

  setDocumentCompleted: (boletinId) =>
    set((state) => ({
      documentStates: {
        ...state.documentStates,
        [boletinId]: {
          ...state.documentStates[boletinId],
          stage: "completed",
          updatedAt: new Date().toISOString(),
        },
      },
    })),

  setDocumentFailed: (boletinId, filename, error, stage) =>
    set((state) => ({
      documentStates: {
        ...state.documentStates,
        [boletinId]: {
          boletinId,
          filename,
          stage: "failed",
          error,
          updatedAt: new Date().toISOString(),
        },
      },
      errors: [
        ...state.errors,
        {
          boletinId,
          filename,
          error,
          stage,
          timestamp: new Date().toISOString(),
        },
      ],
    })),

  setProgress: (current, total, filename, stage) =>
    set({
      progress: { current, total },
      ...(filename ? { currentFilename: filename } : {}),
      ...(stage ? { currentStage: stage } : {}),
    }),

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  setCompleted: (_total: number, _completed: number, _failed: number) =>
    set(() => ({
      isProcessing: false,
      sessionId: null,
      currentStage: "completed",
      // Keep stageHistory and progress so it stays visible after completion
    })),

  setStats: (stats) => set({ stats }),

  setConfig: (config) => set({ config }),

  reset: () =>
    set({
      isProcessing: false,
      sessionId: null,
      progress: { current: 0, total: 0 },
      currentFilename: null,
      currentStage: null,
      stageHistory: [],
      documentStates: {},
      errors: [],
    }),
}))
