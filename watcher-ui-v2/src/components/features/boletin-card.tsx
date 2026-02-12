import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { FileText, Calendar, Building2, Play, RotateCcw, Loader2, FileWarning } from "lucide-react"
import dayjs from "dayjs"
import { cn } from "@/lib/utils"
import type { Boletin } from "@/types"
import { DocumentStatusBadge } from "./document-status-badge"
import { PipelineConfigPanel } from "./pipeline-config-panel"
import { usePipelineProcessOne, usePipelineResetOne } from "@/lib/api/hooks/use-pipeline"
import { usePipelineStore } from "@/lib/store/pipeline-store"
import type { PipelineConfigState } from "@/lib/store/pipeline-store"

interface BoletinCardProps {
  boletin: Boletin
  onView?: (id: number) => void
  className?: string
}

export function BoletinCard({ boletin, onView, className }: BoletinCardProps) {
  const [configOpen, setConfigOpen] = useState(false)
  const processOne = usePipelineProcessOne()
  const resetOne = usePipelineResetOne()
  const documentState = usePipelineStore(
    (s) => s.documentStates[boletin.id]
  )

  // Use real-time state from WebSocket if available, otherwise fall back to REST data
  const displayStatus = documentState?.stage || boletin.status || (boletin.processed ? "completed" : "pending")

  const handleProcess = (config: PipelineConfigState) => {
    processOne.mutate({ boletinId: boletin.id, config })
  }

  const handleReset = (e: React.MouseEvent) => {
    e.stopPropagation()
    resetOne.mutate(boletin.id)
  }

  const isDocProcessing = processOne.isPending || ["extracting", "chunking", "indexing", "cleaning"].includes(displayStatus)
  const hasFile = boletin.has_file !== false

  return (
    <>
      <Card
        className={cn(
          "hover:bg-surface-elevated transition-colors cursor-pointer",
          !hasFile && "opacity-60 border-dashed",
          className
        )}
        onClick={() => onView?.(boletin.id)}
      >
        <CardContent className="p-6">
          <div className="space-y-4">
            {/* Header */}
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3 flex-1">
                <div className={cn(
                  "p-2 rounded-lg",
                  hasFile ? "bg-blue-500/10" : "bg-yellow-500/10"
                )}>
                  {hasFile ? (
                    <FileText className="h-5 w-5 text-blue-400" />
                  ) : (
                    <FileWarning className="h-5 w-5 text-yellow-400" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold truncate">{boletin.filename}</h3>
                  <p className="text-sm text-muted-foreground">
                    {boletin.seccion_nombre || boletin.section}
                  </p>
                  {!hasFile && (
                    <p className="text-xs text-yellow-500 mt-0.5">
                      PDF no disponible en disco
                    </p>
                  )}
                </div>
              </div>
              <DocumentStatusBadge status={displayStatus} />
            </div>

            {/* Info */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Calendar className="h-4 w-4" />
                <span>{dayjs(boletin.date).format("DD/MM/YYYY")}</span>
              </div>
              {boletin.jurisdiccion_nombre && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Building2 className="h-4 w-4" />
                  <span className="truncate">{boletin.jurisdiccion_nombre}</span>
                </div>
              )}
            </div>

            {/* Footer with pipeline controls */}
            <div className="flex items-center justify-between pt-2 border-t">
              <div className="flex items-center gap-1">
                {/* Process Individual */}
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1 text-xs h-7"
                  onClick={(e) => {
                    e.stopPropagation()
                    setConfigOpen(true)
                  }}
                  disabled={isDocProcessing || !hasFile}
                  title={!hasFile ? "PDF no disponible en disco" : "Procesar con configuracion"}
                >
                  {isDocProcessing ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Play className="h-3 w-3" />
                  )}
                  Procesar
                </Button>

                {/* Reset Individual */}
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1 text-xs h-7 text-muted-foreground hover:text-red-400"
                  onClick={handleReset}
                  disabled={
                    resetOne.isPending ||
                    isDocProcessing ||
                    displayStatus === "pending"
                  }
                  title="Reset (volver a pending)"
                >
                  <RotateCcw className="h-3 w-3" />
                  Reset
                </Button>
              </div>

              <Button
                variant="ghost"
                size="sm"
                className="text-xs h-7"
                onClick={(e) => {
                  e.stopPropagation()
                  onView?.(boletin.id)
                }}
              >
                Ver detalle &rarr;
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Per-document Config Panel */}
      <PipelineConfigPanel
        open={configOpen}
        onOpenChange={setConfigOpen}
        onExecute={handleProcess}
        title={`Procesar: ${boletin.filename}`}
      />
    </>
  )
}
