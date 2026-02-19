/**
 * PipelineControls - Main control panel for document processing pipeline.
 * Includes: Process All, Reset Total (double confirm), WebSocket indicator, and progress.
 */

import { useState, useCallback, useEffect } from "react"
// Note: PipelineConfigPanel is still used by individual BoletinCards, not here
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  usePipelineResetAll,
  usePipelineStatus,
} from "@/lib/api/hooks/use-pipeline"
import { usePipelineStore } from "@/lib/store/pipeline-store"
import { useWebSocket } from "@/lib/ws/use-websocket"
import type { WebSocketEvent } from "@/lib/ws/use-websocket"
import { PipelineProgress } from "./pipeline-progress"
import {
  Trash2,
  Wifi,
  WifiOff,
  AlertTriangle,
  Loader2,
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

export function PipelineControls() {
  const [resetDialogOpen, setResetDialogOpen] = useState(false)
  const [resetConfirmText, setResetConfirmText] = useState("")

  const { data: status, refetch: refetchStatus } = usePipelineStatus()
  const resetAll = usePipelineResetAll()

  const {
    isProcessing,
    setProcessing,
    updateDocumentState,
    addStageToHistory,
    setDocumentCompleted,
    setDocumentFailed,
    setProgress,
    setCompleted,
    setStats,
    reset: resetStore,
  } = usePipelineStore()

  // Handle WebSocket events
  const handleWsEvent = useCallback(
    (event: WebSocketEvent) => {
      const d = event.data as Record<string, unknown>

      switch (event.event_type) {
        case "pipeline.started":
          setProcessing(
            d.session_id as string,
            d.total as number
          )
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
          break

        case "pipeline.document.failed":
          setDocumentFailed(
            d.boletin_id as number,
            d.filename as string,
            d.error as string,
            "unknown"
          )
          break

        case "pipeline.completed":
          setCompleted(
            d.total as number,
            d.completed as number,
            d.failed as number
          )
          refetchStatus()
          break

        case "pipeline.reset":
        case "pipeline.reset.document":
          resetStore()
          refetchStatus()
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
      resetStore,
      refetchStatus,
    ]
  )

  const { isConnected } = useWebSocket({
    eventTypes: PIPELINE_EVENTS,
    onEvent: handleWsEvent,
  })

  // Sync stats from REST polling + recover active session on refresh
  useEffect(() => {
    if (status) {
      setStats({
        totalBoletines: status.total_boletines,
        byStatus: status.by_status,
        totalChunks: status.total_chunks,
        totalIndexed: status.total_indexed,
      })
      
      // Recover active session if frontend lost it (e.g. page refresh)
      if (status.active_session && !isProcessing) {
        const s = status.active_session as Record<string, unknown>
        setProcessing(s.session_id as string, (s.stages_total as number) || 4)
        setProgress(
          (s.stages_done as number) || 0,
          (s.stages_total as number) || 4,
          s.filename as string,
          s.stage as string,
        )
      }
    }
  }, [status, setStats, isProcessing, setProcessing, setProgress])

  // Handle reset (requires typing RESET)
  const handleResetConfirm = () => {
    if (resetConfirmText !== "RESET") return
    resetAll.mutate(undefined, {
      onSuccess: () => {
        setResetDialogOpen(false)
        setResetConfirmText("")
      },
    })
  }

  return (
    <>
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Reset All button */}
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

            {/* Status badges */}
            <div className="flex-1" />

            {status && (
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>{status.total_boletines} docs</span>
                <span className="text-green-400">
                  {status.by_status?.completed ?? 0} completados
                </span>
                <span>{status.total_chunks} chunks</span>
                <Badge variant="outline" className="text-xs">
                  {status.by_status?.pending ?? 0} pendientes
                </Badge>
              </div>
            )}

            {/* WebSocket indicator */}
            <div
              className="flex items-center gap-1"
              title={
                isConnected ? "WebSocket conectado" : "WebSocket desconectado"
              }
            >
              {isConnected ? (
                <Wifi className="h-4 w-4 text-green-400" />
              ) : (
                <WifiOff className="h-4 w-4 text-red-400" />
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Progress bar (visible during processing) */}
      <PipelineProgress />

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
                Esta accion eliminara <strong>TODOS</strong> los datos
                procesados:
              </p>
              <ul className="list-disc list-inside text-sm space-y-1 text-muted-foreground">
                <li>Todos los chunk records de SQLite</li>
                <li>Todos los embeddings de ChromaDB</li>
                <li>Todos los archivos .txt extraidos</li>
                <li>El status de todos los documentos volvera a &quot;pending&quot;</li>
              </ul>
              <p className="font-semibold text-red-400">
                Esta accion NO se puede deshacer.
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
              disabled={
                resetConfirmText !== "RESET" || resetAll.isPending
              }
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
    </>
  )
}
