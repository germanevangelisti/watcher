/**
 * Pipeline Status Dashboard - Dedicated dashboard with metrics, state, error log, and activity.
 */

import { useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Progress } from "@/components/ui/progress"
import { usePipelineStatus, usePipelineProcessOne } from "@/lib/api/hooks/use-pipeline"
import { usePipelineStore } from "@/lib/store/pipeline-store"
import { useWebSocket } from "@/lib/ws/use-websocket"
import type { WebSocketEvent } from "@/lib/ws/use-websocket"
import { FadeTransition } from "@/components/ui/fade-transition"
import {
  FileText,
  Layers,
  Database,
  AlertCircle,
  CheckCircle2,
  Clock,
  RotateCcw,
  Wifi,
  WifiOff,
  Activity,
} from "lucide-react"

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

export function PipelineStatusPage() {
  const { data: status, isLoading, refetch } = usePipelineStatus()
  const processOne = usePipelineProcessOne()
  const { errors, isProcessing, progress, currentFilename, currentStage } =
    usePipelineStore()

  // WebSocket for real-time activity feed
  const handleWsEvent = useCallback(() => {
    // Events are handled by PipelineControls; this is just for the activity feed
  }, [])

  const { events: recentEvents, isConnected } = useWebSocket({
    eventTypes: PIPELINE_EVENTS,
    onEvent: handleWsEvent,
  })

  const byStatus = status?.by_status ?? {}
  const total = status?.total_boletines ?? 0
  const completedPct = total > 0 ? Math.round(((byStatus.completed ?? 0) / total) * 100) : 0

  const handleRetry = (boletinId: number) => {
    processOne.mutate({ boletinId })
  }

  return (
    <FadeTransition>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Pipeline Status</h1>
            <p className="text-muted-foreground mt-2">
              Metricas y estado del pipeline de procesamiento
            </p>
          </div>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <Badge variant="outline" className="gap-1 text-green-400 border-green-500/20">
                <Wifi className="h-3 w-3" />
                Conectado
              </Badge>
            ) : (
              <Badge variant="outline" className="gap-1 text-red-400 border-red-500/20">
                <WifiOff className="h-3 w-3" />
                Desconectado
              </Badge>
            )}
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RotateCcw className="h-4 w-4" />
            </Button>
          </div>
        </div>

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

        {/* Pipeline State - Bar Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Estado de Documentos</CardTitle>
            <CardDescription>Distribucion por estado de procesamiento</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <div className="space-y-3">
                {/* Global progress */}
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>Progreso general</span>
                    <span className="text-muted-foreground">{completedPct}%</span>
                  </div>
                  <Progress value={completedPct} className="h-3" />
                </div>

                {/* Status breakdown */}
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

                {/* Active session */}
                {isProcessing && (
                  <div className="mt-4 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                    <div className="flex items-center gap-2 mb-2">
                      <Activity className="h-4 w-4 text-blue-400 animate-pulse" />
                      <span className="text-sm font-medium">Sesion activa</span>
                    </div>
                    <Progress
                      value={
                        progress.total > 0
                          ? (progress.current / progress.total) * 100
                          : 0
                      }
                      className="h-2 mb-1"
                    />
                    <p className="text-xs text-muted-foreground">
                      {progress.current}/{progress.total}
                      {currentFilename && ` - ${currentFilename}`}
                      {currentStage && ` (${currentStage})`}
                    </p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Error Log */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-400" />
                Error Log
              </CardTitle>
              <CardDescription>
                Errores recientes del pipeline
              </CardDescription>
            </CardHeader>
            <CardContent>
              {errors.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No hay errores registrados
                </p>
              ) : (
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {errors.map((err, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg bg-red-500/5 border border-red-500/10 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium truncate">
                          {err.filename}
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 text-xs"
                          onClick={() => handleRetry(err.boletinId)}
                        >
                          <RotateCcw className="h-3 w-3 mr-1" />
                          Reintentar
                        </Button>
                      </div>
                      <p className="text-xs text-red-400 truncate">{err.error}</p>
                      <p className="text-xs text-muted-foreground">
                        Stage: {err.stage} | {new Date(err.timestamp).toLocaleTimeString()}
                      </p>
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
              <CardDescription>
                Eventos del pipeline en tiempo real
              </CardDescription>
            </CardHeader>
            <CardContent>
              {recentEvents.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  {isConnected
                    ? "Esperando eventos..."
                    : "Conectando al WebSocket..."}
                </p>
              ) : (
                <div className="space-y-1 max-h-80 overflow-y-auto">
                  {recentEvents
                    .slice(-20)
                    .reverse()
                    .map((evt, i) => {
                      const d = evt.data as Record<string, unknown>
                      return (
                        <div
                          key={i}
                          className="flex items-start gap-2 py-1.5 border-b border-border/50 last:border-0"
                        >
                          <div className="mt-0.5">
                            <EventDot type={evt.event_type} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs truncate">
                              <span className="font-medium">
                                {formatEventType(evt.event_type)}
                              </span>
                              {d.filename && (
                                <span className="text-muted-foreground">
                                  {" "} - {d.filename as string}
                                </span>
                              )}
                            </p>
                            <p className="text-xs text-muted-foreground">
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
    </FadeTransition>
  )
}

// Helper components
function EventDot({ type }: { type: string }) {
  let color = "bg-zinc-400"
  if (type.includes("completed")) color = "bg-green-400"
  else if (type.includes("failed")) color = "bg-red-400"
  else if (type.includes("started") || type.includes("stage")) color = "bg-blue-400"
  else if (type.includes("reset")) color = "bg-yellow-400"

  return <div className={`h-2 w-2 rounded-full ${color}`} />
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

export default PipelineStatusPage
