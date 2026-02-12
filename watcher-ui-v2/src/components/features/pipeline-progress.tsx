/**
 * PipelineProgress - Shows progress bar + stage timeline for pipeline processing.
 * Tracks 5 stages: extraction, cleaning, chunking, indexing, completed.
 */

import { Progress } from "@/components/ui/progress"
import { Card, CardContent } from "@/components/ui/card"
import { usePipelineStore } from "@/lib/store/pipeline-store"
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Circle,
  FileSearch,
  Sparkles,
  Scissors,
  Database,
  PartyPopper,
} from "lucide-react"
import { cn } from "@/lib/utils"

// Ordered pipeline stages
const PIPELINE_STAGES = [
  { key: "extracting", label: "Extraccion", icon: FileSearch },
  { key: "cleaning", label: "Limpieza", icon: Sparkles },
  { key: "chunking", label: "Chunking", icon: Scissors },
  { key: "indexing", label: "Indexacion", icon: Database },
  { key: "completed", label: "Completado", icon: PartyPopper },
] as const

type StageKey = typeof PIPELINE_STAGES[number]["key"]

function getStageIndex(stage: string): number {
  return PIPELINE_STAGES.findIndex((s) => s.key === stage)
}

export function PipelineProgress() {
  const {
    isProcessing,
    progress,
    currentFilename,
    currentStage,
    stageHistory,
    errors,
  } = usePipelineStore()

  // Only show when there's an active or recently completed pipeline
  if (!isProcessing && progress.total === 0 && stageHistory.length === 0) return null

  const percentage =
    progress.total > 0
      ? Math.round((progress.current / progress.total) * 100)
      : 0

  const currentStageIdx = currentStage ? getStageIndex(currentStage) : -1
  const completedStages = new Set(stageHistory.map((s) => s.stage))
  const hasFailed = errors.length > 0
  const isComplete = currentStage === "completed" || completedStages.has("completed")

  return (
    <Card
      className={cn(
        "transition-colors",
        isProcessing
          ? "border-blue-500/20 bg-blue-500/5"
          : isComplete && !hasFailed
            ? "border-green-500/20 bg-green-500/5"
            : hasFailed
              ? "border-red-500/20 bg-red-500/5"
              : "border-muted"
      )}
    >
      <CardContent className="p-4">
        <div className="space-y-4">
          {/* Header with progress */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isProcessing ? (
                <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
              ) : isComplete && !hasFailed ? (
                <CheckCircle2 className="h-4 w-4 text-green-400" />
              ) : hasFailed ? (
                <XCircle className="h-4 w-4 text-red-400" />
              ) : (
                <CheckCircle2 className="h-4 w-4 text-green-400" />
              )}
              <span className="text-sm font-medium">
                {isProcessing
                  ? `Procesando: ${currentFilename || "..."}`
                  : isComplete && !hasFailed
                    ? `Completado: ${currentFilename || ""}`
                    : hasFailed
                      ? `Error en: ${currentFilename || ""}`
                      : "Pipeline listo"}
              </span>
            </div>
            <span className="text-sm font-mono text-muted-foreground">
              {percentage}%
            </span>
          </div>

          {/* Progress Bar */}
          <Progress value={percentage} className="h-2" />

          {/* Stage Timeline */}
          <div className="flex items-center justify-between gap-1">
            {PIPELINE_STAGES.map((stage, idx) => {
              const isDone = completedStages.has(stage.key)
              const isCurrent = currentStage === stage.key && isProcessing
              const isPast = idx < currentStageIdx
              const isActive = isDone || isCurrent || isPast
              const Icon = stage.icon

              return (
                <div key={stage.key} className="flex flex-col items-center flex-1">
                  {/* Icon + connector */}
                  <div className="flex items-center w-full">
                    {/* Left connector line */}
                    {idx > 0 && (
                      <div
                        className={cn(
                          "h-0.5 flex-1 transition-colors",
                          isPast || isDone
                            ? "bg-green-500"
                            : isCurrent
                              ? "bg-blue-500"
                              : "bg-muted"
                        )}
                      />
                    )}

                    {/* Stage icon */}
                    <div
                      className={cn(
                        "flex items-center justify-center rounded-full w-8 h-8 shrink-0 transition-all",
                        isDone
                          ? "bg-green-500/20 text-green-400"
                          : isCurrent
                            ? "bg-blue-500/20 text-blue-400 ring-2 ring-blue-500/40"
                            : isPast
                              ? "bg-green-500/20 text-green-400"
                              : "bg-muted/50 text-muted-foreground"
                      )}
                    >
                      {isDone || isPast ? (
                        <CheckCircle2 className="h-4 w-4" />
                      ) : isCurrent ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Icon className="h-4 w-4" />
                      )}
                    </div>

                    {/* Right connector line */}
                    {idx < PIPELINE_STAGES.length - 1 && (
                      <div
                        className={cn(
                          "h-0.5 flex-1 transition-colors",
                          isPast || isDone
                            ? idx + 1 <= currentStageIdx || completedStages.has(PIPELINE_STAGES[idx + 1]?.key)
                              ? "bg-green-500"
                              : isCurrent
                                ? "bg-blue-500/40"
                                : "bg-muted"
                            : "bg-muted"
                        )}
                      />
                    )}
                  </div>

                  {/* Label */}
                  <span
                    className={cn(
                      "text-[10px] mt-1 text-center leading-tight",
                      isDone || isPast
                        ? "text-green-400"
                        : isCurrent
                          ? "text-blue-400 font-medium"
                          : "text-muted-foreground"
                    )}
                  >
                    {stage.label}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
