/**
 * PipelineWorkflowPage - Dedicated pipeline workflow dashboard.
 * Combines execution controls, detailed task monitoring, and real-time progress.
 */

import { useState, useCallback, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  usePipelineStatus,
  usePipelineProcessAll,
  usePipelineProcessOne,
  usePipelineResetAll,
  usePipelineResetOne,
} from "@/lib/api/hooks/use-pipeline"
import { usePipelineStore } from "@/lib/store/pipeline-store"
import { useWebSocket } from "@/lib/ws/use-websocket"
import type { WebSocketEvent } from "@/lib/ws/use-websocket"
import { PipelineProgress } from "@/components/features/pipeline-progress"
import { PipelineConfigPanel } from "@/components/features/pipeline-config-panel"
import type { PipelineConfigState } from "@/lib/store/pipeline-store"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import {
  Play,
  PlayCircle,
  Trash2,
  RotateCcw,
  Wifi,
  WifiOff,
  AlertTriangle,
  Loader2,
  FileText,
  Layers,
  Database,
  AlertCircle,
  CheckCircle2,
  Clock,
  Activity,
  Settings2,
  FileSearch,
  Sparkles,
  Scissors,
  ArrowRight,
} from "lucide-react"

// Pipeline event types to subscribe to
const PIPELINE_EVENTS = [
  "pipeline.reset",
  "pipeline.reset.document",
  "pipeline.started",
  "pipeline.document.started",
  "pipeline.document.stage",
  "pipeline.document.completed",
  "pipeline.document.failed",
  "pipeline.completed",
]

// Stage info for task detail view
const STAGE_INFO: Record<string, { label: string; icon: typeof FileSearch; color: string }> = {
  extracting: { label: "Extracción", icon: FileSearch, color: "text-blue-400" },
  cleaning: { label: "Limpieza", icon: Sparkles, color: "text-purple-400" },
  chunking: { label: "Chunking", icon: Scissors, color: "text-yellow-400" },
  indexing: { label: "Indexación", icon: Database, color: "text-orange-400" },
  completed: { label: "Completado", icon: CheckCircle2, color: "text-green-400" },
  failed: { label: "Fallido", icon: AlertCircle, color: "text-red-400" },
}

export function PipelineWorkflowPage() {
  const [resetDialogOpen, setResetDialogOpen] = useState(false)
  const [resetConfirmText, setResetConfirmText] = useState("")
  const [configOpen, setConfigOpen] = useState(false)
  const [selectedBoletinId, setSelectedBoletinId] = useState<number | null>(null)

  const { data: status, isLoading, refetch: refetchStatus } = usePipelineStatus()
  const processAll = usePipelineProcessAll()
  const processOne = usePipelineProcessOne()
  const resetAll = usePipelineResetAll()
  const resetOne = usePipelineResetOne()

  const store = usePipelineStore()
  const {
    isProcessing,
    progress,
    currentFilename,
    currentStage,
    stageHistory,
    documentStates,
    errors,
    setProcessing,
    updateDocumentState,
    addStageToHistory,
    setDocumentCompleted,
    setDocumentFailed,
    setProgress,
    setCompleted,
    setStats,
    reset: resetStore,
  } = store

  // Handle WebSocket events with toast notifications
  const handleWsEvent = useCallback(
    (event: WebSocketEvent) => {
      const d = event.data as Record<string, unknown>

      switch (event.event_type) {
        case "pipeline.started":
          setProcessing(d.session_id as string, d.total as number)
          toast.info("Pipeline iniciado", {
            description: `Procesando ${d.total} documentos`,
          })
          break

        case "pipeline.document.started":
          if (d.progress) {
            const prog = d.progress as { current: number; total: number }
            setProgress(prog.current, prog.total, d.filename as string)
          }
          break

        case "pipeline.document.stage":
          updateDocumentState(
            d.boletin_id as number,
            d.filename as string,
            d.stage as string
          )
          addStageToHistory(
            d.stage as string,
            d.details as Record<string, unknown> | undefined
          )
          if (d.progress) {
            const prog = d.progress as { current: number; total: number }
            setProgress(prog.current, prog.total, d.filename as string, d.stage as string)
          }
          break

        case "pipeline.document.completed":
          setDocumentCompleted(d.boletin_id as number)
          toast.success(`Documento completado`, {
            description: d.filename as string,
          })
          break

        case "pipeline.document.failed":
          setDocumentFailed(
            d.boletin_id as number,
            d.filename as string,
            d.error as string,
            "unknown"
          )
          toast.error(`Documento fallido`, {
            description: `${d.filename}: ${d.error}`,
          })
          break

        case "pipeline.completed": {
          const completed = d.completed as number
          const failed = d.failed as number
          setCompleted(d.total as number, completed, failed)
          refetchStatus()
          toast.success("Pipeline completado", {
            description: `${completed} exitosos, ${failed} fallidos`,
          })
          break
        }

        case "pipeline.reset":
        case "pipeline.reset.document":
          resetStore()
          refetchStatus()
          toast.info("Pipeline reseteado")
          break
      }
    },
    [
      setProcessing,
      updateDocumentState,
      addStageToHistory,
      setDocumentCompleted,
      setDocumentFailed,
      setProgress,
      setCompleted,
      setStats,
      resetStore,
      refetchStatus,
    ]
  )

  const { events: recentEvents, isConnected } = useWebSocket({
    eventTypes: PIPELINE_EVENTS,
    onEvent: handleWsEvent,
  })

  // Sync stats from REST
  useEffect(() => {
    if (status) {
      setStats({
        totalBoletines: status.total_boletines,
        byStatus: status.by_status,
        totalChunks: status.total_chunks,
        totalIndexed: status.total_indexed,
      })

      // Recover active session if frontend lost it
      if (status.active_session && !isProcessing) {
        const s = status.active_session as Record<string, unknown>
        setProcessing(s.session_id as string, (s.stages_total as number) || 4)
        setProgress(
          (s.stages_done as number) || 0,
          (s.stages_total as number) || 4,
          s.filename as string,
          s.stage as string
        )
      }
    }
  }, [status, setStats, isProcessing, setProcessing, setProgress])

  const byStatus = status?.by_status ?? {}
  const total = status?.total_boletines ?? 0
  const completedPct = total > 0 ? Math.round(((byStatus.completed ?? 0) / total) * 100) : 0

  // Execution handlers
  const handleProcessAll = (config: PipelineConfigState) => {
    processAll.mutate(config)
    setConfigOpen(false)
    toast.info("Iniciando procesamiento de todos los documentos pendientes...")
  }

  const handleProcessOne = (config: PipelineConfigState) => {
    if (selectedBoletinId) {
      processOne.mutate({ boletinId: selectedBoletinId, config })
      setConfigOpen(false)
      setSelectedBoletinId(null)
    }
  }

  const handleRetry = (boletinId: number) => {
    processOne.mutate({ boletinId })
    toast.info("Reintentando documento...")
  }

  const handleResetConfirm = () => {
    if (resetConfirmText !== "RESET") return
    resetAll.mutate(undefined, {
      onSuccess: () => {
        setResetDialogOpen(false)
        setResetConfirmText("")
        toast.success("Pipeline reseteado completamente")
      },
    })
  }

  // Calculate ETA
  const getETA = () => {
    if (!isProcessing || progress.total === 0 || progress.current === 0) return null
    const avgHistory = stageHistory.length
    if (avgHistory < 2) return null
    const remaining = progress.total - progress.current
    // Rough estimate: ~30s per document (we could track actual times)
    return `~${Math.ceil(remaining * 0.5)} min`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Pipeline de Procesamiento</h1>
          <p className="text-muted-foreground mt-2">
            Ejecuta, monitorea y gestiona el pipeline de documentos
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <Badge variant="outline" className="gap-1 text-green-400 border-green-500/20">
              <Wifi className="h-3 w-3" />
              Tiempo real
            </Badge>
          ) : (
            <Badge variant="outline" className="gap-1 text-red-400 border-red-500/20">
              <WifiOff className="h-3 w-3" />
              Sin conexión
            </Badge>
          )}
          <Button variant="outline" size="sm" onClick={() => refetchStatus()}>
            <RotateCcw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Execution Controls */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-sm flex items-center gap-2">
            <Settings2 className="h-4 w-4" />
            Controles de Ejecución
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-3">
            <Button
              className="gap-2"
              onClick={() => {
                setSelectedBoletinId(null)
                setConfigOpen(true)
              }}
              disabled={isProcessing || (byStatus.pending ?? 0) === 0}
            >
              <PlayCircle className="h-4 w-4" />
              Procesar Todos ({byStatus.pending ?? 0} pendientes)
            </Button>

            <Button
              variant="outline"
              className="gap-2"
              onClick={() => refetchStatus()}
            >
              <RotateCcw className="h-4 w-4" />
              Actualizar Estado
            </Button>

            <div className="flex-1" />

            <Button
              size="sm"
              variant="destructive"
              className="gap-2"
              onClick={() => setResetDialogOpen(true)}
              disabled={isProcessing || resetAll.isPending}
            >
              <Trash2 className="h-4 w-4" />
              Reset Total
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Real-time Progress */}
      <PipelineProgress />

      {/* Enhanced active session display */}
      {isProcessing && (
        <Card className="border-blue-500/20 bg-blue-500/5">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-blue-400 animate-pulse" />
                <span className="font-medium text-sm">Sesión activa</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                {getETA() && <span>ETA: {getETA()}</span>}
                <span className="font-mono">
                  {progress.current}/{progress.total}
                </span>
              </div>
            </div>
            <Progress
              value={progress.total > 0 ? (progress.current / progress.total) * 100 : 0}
              className="h-3 mb-2"
            />
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {currentFilename && (
                  <>
                    <FileText className="h-3 w-3 inline mr-1" />
                    {currentFilename}
                  </>
                )}
              </span>
              {currentStage && (
                <Badge variant="secondary" className="text-xs gap-1">
                  {STAGE_INFO[currentStage]
                    ? (() => { const Info = STAGE_INFO[currentStage]; const Icon = Info.icon; return <Icon className={cn("h-3 w-3", Info.color)} /> })()
                    : null}
                  {STAGE_INFO[currentStage]?.label || currentStage}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Metrics Grid */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <FileText className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Total Documentos</p>
                  <p className="text-2xl font-bold">{total}</p>
                </div>
              </div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <CheckCircle2 className="h-3 w-3 text-green-400" />
                {byStatus.completed ?? 0} completados ({completedPct}%)
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 rounded-lg bg-yellow-500/10">
                  <Layers className="h-5 w-5 text-yellow-400" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Total Chunks</p>
                  <p className="text-2xl font-bold">{status?.total_chunks ?? 0}</p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">Fragmentos generados</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 rounded-lg bg-orange-500/10">
                  <Database className="h-5 w-5 text-orange-400" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Embeddings Indexados</p>
                  <p className="text-2xl font-bold">{status?.total_indexed ?? 0}</p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">En ChromaDB</p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 rounded-lg bg-red-500/10">
                  <AlertCircle className="h-5 w-5 text-red-400" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Pendientes / Fallidos</p>
                  <p className="text-2xl font-bold">
                    {(byStatus.pending ?? 0) + (byStatus.failed ?? 0)}
                  </p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                {byStatus.pending ?? 0} pendientes, {byStatus.failed ?? 0} fallidos
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Status breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Estado de Documentos</CardTitle>
          <CardDescription>Distribución por estado de procesamiento</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span>Progreso general</span>
                <span className="text-muted-foreground">{completedPct}%</span>
              </div>
              <Progress value={completedPct} className="h-3" />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 pt-3">
              {(
                [
                  ["pending", "Pendientes", "bg-zinc-400"],
                  ["extracting", "Extrayendo", "bg-blue-400"],
                  ["chunking", "Chunking", "bg-yellow-400"],
                  ["indexing", "Indexando", "bg-orange-400"],
                  ["completed", "Completados", "bg-green-400"],
                  ["failed", "Fallidos", "bg-red-400"],
                ] as const
              ).map(([key, label, color]) => (
                <div key={key} className="flex items-center gap-2">
                  <div className={`h-3 w-3 rounded-full ${color}`} />
                  <span className="text-sm">{label}</span>
                  <span className="text-sm font-mono text-muted-foreground ml-auto">
                    {byStatus[key] ?? 0}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Document Task Detail + Activity Feed */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Document Processing Detail */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Play className="h-4 w-4 text-blue-400" />
              Detalle de Tareas
            </CardTitle>
            <CardDescription>
              Estado por documento en la sesión actual
            </CardDescription>
          </CardHeader>
          <CardContent>
            {Object.keys(documentStates).length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No hay documentos en procesamiento activo
              </p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {Object.entries(documentStates).map(([id, state]) => {
                  const stageInfo = STAGE_INFO[state.stage] || {
                    label: state.stage,
                    icon: FileText,
                    color: "text-muted-foreground",
                  }
                  const StageIcon = stageInfo.icon

                  return (
                    <div
                      key={id}
                      className={cn(
                        "p-3 rounded-lg border space-y-2",
                        state.stage === "completed"
                          ? "bg-green-500/5 border-green-500/10"
                          : state.stage === "failed"
                            ? "bg-red-500/5 border-red-500/10"
                            : "bg-muted/30 border-border/50"
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                          <StageIcon className={cn("h-4 w-4 shrink-0", stageInfo.color)} />
                          <span className="text-sm font-medium truncate">
                            {state.filename}
                          </span>
                        </div>
                        <Badge
                          variant="secondary"
                          className={cn("text-xs shrink-0", stageInfo.color)}
                        >
                          {stageInfo.label}
                        </Badge>
                      </div>

                      {/* Mini stage timeline */}
                      <div className="flex items-center gap-1">
                        {["extracting", "cleaning", "chunking", "indexing", "completed"].map(
                          (stageName, idx) => {
                            const stageIdx = ["extracting", "cleaning", "chunking", "indexing", "completed"].indexOf(state.stage)
                            const isDone = idx < stageIdx || state.stage === "completed"
                            const isCurrent = stageName === state.stage && state.stage !== "completed" && state.stage !== "failed"

                            return (
                              <div key={stageName} className="flex items-center flex-1">
                                <div
                                  className={cn(
                                    "h-1.5 flex-1 rounded-full transition-colors",
                                    isDone
                                      ? "bg-green-500"
                                      : isCurrent
                                        ? "bg-blue-500 animate-pulse"
                                        : "bg-muted"
                                  )}
                                />
                                {idx < 4 && <ArrowRight className="h-2.5 w-2.5 text-muted-foreground/30 mx-0.5 shrink-0" />}
                              </div>
                            )
                          }
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Error Log + Activity columns */}
        <div className="space-y-6">
          {/* Error Log */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-400" />
                Errores ({errors.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {errors.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  Sin errores
                </p>
              ) : (
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {errors.slice(-5).reverse().map((err, i) => (
                    <div
                      key={i}
                      className="p-2.5 rounded-lg bg-red-500/5 border border-red-500/10 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium truncate">{err.filename}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-5 text-[10px] px-1.5"
                          onClick={() => handleRetry(err.boletinId)}
                        >
                          <RotateCcw className="h-2.5 w-2.5 mr-1" />
                          Reintentar
                        </Button>
                      </div>
                      <p className="text-[10px] text-red-400 truncate">{err.error}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Clock className="h-4 w-4 text-blue-400" />
                Actividad Reciente
              </CardTitle>
            </CardHeader>
            <CardContent>
              {recentEvents.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  {isConnected ? "Esperando eventos..." : "Conectando..."}
                </p>
              ) : (
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {recentEvents
                    .slice(-15)
                    .reverse()
                    .map((evt, i) => {
                      const d = evt.data as Record<string, string>
                      return (
                        <div
                          key={i}
                          className="flex items-start gap-2 py-1 border-b border-border/30 last:border-0"
                        >
                          <EventDot type={evt.event_type} />
                          <div className="flex-1 min-w-0">
                            <p className="text-[11px] truncate">
                              <span className="font-medium">
                                {formatEventType(evt.event_type)}
                              </span>
                              {d.filename && (
                                <span className="text-muted-foreground"> - {d.filename}</span>
                              )}
                            </p>
                            <p className="text-[10px] text-muted-foreground">
                              {new Date(evt.timestamp).toLocaleTimeString()}
                              {d.stage && ` | ${d.stage}`}
                            </p>
                          </div>
                        </div>
                      )
                    })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Pipeline Config Panel */}
      <PipelineConfigPanel
        open={configOpen}
        onOpenChange={setConfigOpen}
        onExecute={selectedBoletinId ? handleProcessOne : handleProcessAll}
        title={
          selectedBoletinId
            ? `Procesar documento #${selectedBoletinId}`
            : "Procesar todos los pendientes"
        }
      />

      {/* Reset Double Confirmation Dialog */}
      <Dialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-400">
              <AlertTriangle className="h-5 w-5" />
              Reset Total de Datos
            </DialogTitle>
            <DialogDescription className="space-y-2">
              <p>
                Esta acción eliminará <strong>TODOS</strong> los datos procesados:
              </p>
              <ul className="list-disc list-inside text-sm space-y-1 text-muted-foreground">
                <li>Todos los chunk records de SQLite</li>
                <li>Todos los embeddings de ChromaDB</li>
                <li>Todos los archivos .txt extraídos</li>
                <li>El status de todos los documentos volverá a &quot;pending&quot;</li>
              </ul>
              <p className="font-semibold text-red-400">
                Esta acción NO se puede deshacer.
              </p>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2 py-2">
            <label className="text-sm text-muted-foreground">
              Escribe <strong>RESET</strong> para confirmar:
            </label>
            <Input
              value={resetConfirmText}
              onChange={(e) => setResetConfirmText(e.target.value)}
              placeholder="Escribe RESET"
              className="font-mono"
            />
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setResetDialogOpen(false)
                setResetConfirmText("")
              }}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleResetConfirm}
              disabled={resetConfirmText !== "RESET" || resetAll.isPending}
            >
              {resetAll.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Trash2 className="h-4 w-4 mr-2" />
              )}
              Eliminar Todo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// Helper components
function EventDot({ type }: { type: string }) {
  let color = "bg-zinc-400"
  if (type.includes("completed")) color = "bg-green-400"
  else if (type.includes("failed")) color = "bg-red-400"
  else if (type.includes("started") || type.includes("stage")) color = "bg-blue-400"
  else if (type.includes("reset")) color = "bg-yellow-400"

  return <div className={`h-2 w-2 rounded-full mt-1.5 shrink-0 ${color}`} />
}

function formatEventType(type: string): string {
  const map: Record<string, string> = {
    "pipeline.started": "Pipeline iniciado",
    "pipeline.completed": "Pipeline completado",
    "pipeline.reset": "Reset total",
    "pipeline.reset.document": "Reset documento",
    "pipeline.document.started": "Doc iniciado",
    "pipeline.document.stage": "Stage",
    "pipeline.document.completed": "Doc completado",
    "pipeline.document.failed": "Doc fallido",
  }
  return map[type] || type
}
