import { useState, useCallback } from "react"
import dayjs from "dayjs"
import localizedFormat from "dayjs/plugin/localizedFormat"
import "dayjs/locale/es"
import { ChevronLeft, ChevronRight, Loader2, RotateCcw, CheckCircle2, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useBoletinCalendar } from "@/lib/api/hooks/use-boletin-calendar"
import { useTriggerFromDate, useTriggerDay, useTriggerMonth } from "@/lib/api/hooks/use-pipeline-trigger"
import { usePipelineResetOne } from "@/lib/api/hooks/use-pipeline"
import { useWebSocket } from "@/lib/ws/use-websocket"
import type { WebSocketEvent } from "@/lib/ws/use-websocket"
import { usePipelineStore } from "@/lib/store/pipeline-store"
import type { StageHistoryEntry } from "@/lib/store/pipeline-store"
import { useQueryClient } from "@tanstack/react-query"
import { useRouter } from "@tanstack/react-router"
import type { SeccionDia, JurisdiccionCalendar } from "@/types"

dayjs.extend(localizedFormat)
dayjs.locale("es")

// ─── Helpers ─────────────────────────────────────────────────────────────────

type StatusColor = {
  dot: string
  badge: string
  label: string
}

const STATUS_STYLE: Record<string, StatusColor> = {
  completed:  { dot: "bg-green-500",  badge: "bg-green-100 text-green-800",   label: "Completado" },
  pending:    { dot: "bg-yellow-400", badge: "bg-yellow-100 text-yellow-800", label: "Pendiente" },
  processing: { dot: "bg-blue-400",   badge: "bg-blue-100 text-blue-800",     label: "Procesando" },
  error:      { dot: "bg-red-500",    badge: "bg-red-100 text-red-800",       label: "Error" },
  not_found:  { dot: "bg-gray-300",   badge: "bg-gray-100 text-gray-500",     label: "No encontrado" },
}

const STAGE_LABELS: Record<string, string> = {
  extracting:    "Extrayendo",
  cleaning:      "Limpiando",
  entity_mapping:"Mapeando entidades",
  chunking:      "Fragmentando",
  indexing:      "Indexando",
  analyzing:     "Analizando",
}

function stageMessage(entry: StageHistoryEntry): string {
  const d = entry.details ?? {}
  switch (entry.stage) {
    case "extracting":     return "Extrayendo PDF"
    case "cleaning":       return "Limpiando texto"
    case "entity_mapping": return "Mapeando entidades"
    case "chunking":       return "Fragmentando texto"
    case "indexing":       return `Indexando${d.chunks_created != null ? ` ${d.chunks_created} chunks` : ""}`
    case "analyzing":      return `Análisis Gemini${d.chunks_indexed != null ? ` (${d.chunks_indexed} chunks)` : ""}`
    case "completed":      return `Completado${d.actos_extracted != null ? ` · ${d.actos_extracted} actos` : ""}`
    case "failed":         return `Error: ${String(d.error ?? "desconocido")}`
    default:               return entry.stage
  }
}

function dotClass(status: string): string {
  return `w-2 h-2 rounded-full inline-block ${STATUS_STYLE[status]?.dot ?? "bg-gray-300"}`
}

// Generate list of weekday dates (Mon–Fri) for a given year+month
function getWeekdays(year: number, month: number): string[] {
  const days: string[] = []
  const daysInMonth = dayjs(`${year}-${String(month).padStart(2, "0")}-01`).daysInMonth()
  for (let d = 1; d <= daysInMonth; d++) {
    const date = dayjs(`${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`)
    if (date.day() !== 0 && date.day() !== 6) {
      days.push(date.format("YYYYMMDD"))
    }
  }
  return days
}

// Compute the Monday of a weekday's ISO week (no plugin needed)
function mondayOf(dateStr: string): string {
  const d = dayjs(dateStr, "YYYYMMDD")
  const dow = d.day() // 0=Sun, 1=Mon, ..., 6=Sat
  const isoDay = dow === 0 ? 7 : dow  // 1=Mon … 7=Sun
  return d.subtract(isoDay - 1, "day").format("YYYYMMDD")
}

// Group weekdays into ISO weeks (Mon–Fri rows)
function groupByWeek(days: string[]): string[][] {
  const weekMap = new Map<string, string[]>()
  const weekOrder: string[] = []
  for (const d of days) {
    const monday = mondayOf(d)
    if (!weekMap.has(monday)) {
      weekMap.set(monday, [])
      weekOrder.push(monday)
    }
    weekMap.get(monday)!.push(d)
  }
  return weekOrder.map((k) => weekMap.get(k)!)
}

// ─── Sub-components ───────────────────────────────────────────────────────────

interface DayCellProps {
  dateStr: string
  secciones: SeccionDia[] | undefined
  isToday: boolean
  isSelected: boolean
  isFuture: boolean
  onClick: () => void
}

function DayCell({ dateStr, secciones, isToday, isSelected, isFuture, onClick }: DayCellProps) {
  const day = dayjs(dateStr, "YYYYMMDD")
  const hasData = secciones && secciones.length > 0

  return (
    <button
      onClick={onClick}
      className={`
        w-full rounded-lg p-1.5 text-left transition-colors
        ${isFuture ? "opacity-35 cursor-default" : "hover:bg-muted/60"}
        ${isSelected ? "ring-2 ring-primary bg-muted/40" : ""}
        ${isToday ? "bg-primary/5" : ""}
      `}
    >
      <div className={`text-xs font-medium mb-1 ${isToday ? "text-primary" : "text-muted-foreground"}`}>
        {day.date()}
      </div>
      {isFuture ? (
        <div className="flex flex-wrap gap-0.5">
          {[1, 2, 3, 4, 5].map((n) => (
            <span key={n} className="w-2 h-2 rounded-full inline-block border border-muted-foreground/20" />
          ))}
        </div>
      ) : hasData ? (
        <div className="flex flex-wrap gap-0.5">
          {secciones!.map((s) => (
            <span key={s.numero} className={dotClass(s.status)} title={`S${s.numero}: ${s.nombre}`} />
          ))}
        </div>
      ) : (
        <div className="flex flex-wrap gap-0.5">
          {[1, 2, 3, 4, 5].map((n) => (
            <span key={n} className={dotClass("not_found")} />
          ))}
        </div>
      )}
    </button>
  )
}

interface DayDetailPanelProps {
  dateStr: string
  jurisdiccion: JurisdiccionCalendar
  isFuture: boolean
}

function DayDetailPanel({ dateStr, jurisdiccion, isFuture }: DayDetailPanelProps) {
  const router = useRouter()
  const triggerFromDate = useTriggerFromDate()
  const triggerDay = useTriggerDay()
  const resetOne = usePipelineResetOne()
  const documentStates = usePipelineStore((s) => s.documentStates)
  const dia = jurisdiccion.dias[dateStr]
  const secciones = dia?.secciones ?? []
  const dateLabel = dayjs(dateStr, "YYYYMMDD").format("dddd D [de] MMMM YYYY")

  function handleTrigger(section: string) {
    triggerFromDate.mutate({ jurisdiccion_id: jurisdiccion.id, date: dateStr, section })
  }

  function handleTriggerDay() {
    // Trigger all sections that are not currently processing
    const processingIds = new Set(
      secciones
        .filter((s) => {
          const live = s.boletin_id ? documentStates[s.boletin_id] : undefined
          const stage = live?.stage
          return stage && stage !== "completed" && stage !== "failed"
        })
        .map((s) => s.numero)
    )
    const sectionsToTrigger = secciones.length === 0
      ? ["1", "2", "3", "4", "5"]
      : secciones
          .filter((s) => !processingIds.has(s.numero))
          .map((s) => String(s.numero))
    if (sectionsToTrigger.length > 0) {
      triggerDay.mutate({ jurisdiccion_id: jurisdiccion.id, date: dateStr, sections: sectionsToTrigger })
    }
  }

  return (
    <Card className="mt-4">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium capitalize">{dateLabel}</CardTitle>
          {!isFuture && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              disabled={triggerDay.isPending}
              onClick={handleTriggerDay}
            >
              {triggerDay.isPending
                ? <Loader2 className="h-3 w-3 animate-spin mr-1" />
                : null
              }
              Procesar día
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {isFuture ? (
          <p className="text-sm text-muted-foreground italic">
            Aún no publicado. Los boletines de este día no están disponibles.
          </p>
        ) : secciones.length === 0 ? (
          <p className="text-sm text-muted-foreground">Sin datos para este día.</p>
        ) : (
          secciones.map((s) => {
            // Real-time stage from pipeline store (updated via WebSocket events)
            const liveState = s.boletin_id ? documentStates[s.boletin_id] : undefined
            const liveStage = liveState?.stage
            const history = liveState?.history ?? []

            // Resolve effective status: prefer live pipeline state over DB state
            const effectiveStatus = liveStage
              ? liveStage === "completed" ? "completed"
              : liveStage === "failed" ? "error"
              : "processing"
              : s.status

            const style = STATUS_STYLE[effectiveStatus] ?? STATUS_STYLE.not_found
            const stageLabel = liveStage ? STAGE_LABELS[liveStage] : null
            const isProcessing = effectiveStatus === "processing"

            return (
              <div key={s.numero} className="space-y-0">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    {isProcessing
                      ? <Loader2 className="shrink-0 h-2 w-2 animate-spin text-blue-400" />
                      : <span className={`shrink-0 ${dotClass(effectiveStatus)}`} />
                    }
                    <span className="text-sm truncate">
                      <span className="font-medium text-muted-foreground mr-1">S{s.numero}</span>
                      {s.nombre}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style.badge}`}>
                      {stageLabel ?? style.label}
                    </span>

                    {/* Ver análisis — sección completada */}
                    {effectiveStatus === "completed" && s.boletin_id && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-6 text-xs"
                          onClick={() =>
                            router.navigate({ to: "/documentos/$id", params: { id: String(s.boletin_id) } })
                          }
                        >
                          Ver
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                          disabled={resetOne.isPending}
                          title="Resetear y reprocesar"
                          onClick={() => resetOne.mutate(s.boletin_id!)}
                        >
                          <RotateCcw className="h-3 w-3" />
                        </Button>
                      </>
                    )}

                    {/* Acción para secciones no procesadas o con error */}
                    {(effectiveStatus === "not_found" || effectiveStatus === "pending" || effectiveStatus === "error") && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-6 text-xs"
                        disabled={triggerFromDate.isPending}
                        onClick={() => handleTrigger(s.numero)}
                      >
                        {triggerFromDate.isPending
                          ? <Loader2 className="h-3 w-3 animate-spin" />
                          : effectiveStatus === "not_found" ? "Descargar"
                          : effectiveStatus === "error" ? "Reintentar"
                          : "Procesar"
                        }
                      </Button>
                    )}
                  </div>
                </div>

                {/* Log panel: visible while processing or when history exists */}
                {history.length > 0 && (
                  <div className="ml-4 mt-1 mb-1 pl-3 border-l border-border/50 space-y-0.5">
                    {history.map((entry, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        {entry.stage === "completed"
                          ? <CheckCircle2 className="h-3 w-3 text-green-500 shrink-0" />
                          : entry.stage === "failed"
                          ? <XCircle className="h-3 w-3 text-red-500 shrink-0" />
                          : i === history.length - 1
                          ? <Loader2 className="h-3 w-3 animate-spin text-blue-400 shrink-0" />
                          : <CheckCircle2 className="h-3 w-3 text-muted-foreground/40 shrink-0" />
                        }
                        <span>{stageMessage(entry)}</span>
                        <span className="ml-auto text-muted-foreground/30 tabular-nums">
                          {dayjs(entry.timestamp).format("HH:mm:ss")}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })
        )}
      </CardContent>
    </Card>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

interface BoletinCalendarProps {
  jurisdiccionId?: number
}

const ALL_SECTIONS = ["1", "2", "3", "4", "5"]
const DEFAULT_SECTIONS = ["1", "3", "4"]
const SECTION_SHORT: Record<string, string> = {
  "1": "S1", "2": "S2", "3": "S3", "4": "S4", "5": "S5",
}

export function BoletinCalendar({ jurisdiccionId }: BoletinCalendarProps) {
  const today = dayjs()
  const [current, setCurrent] = useState({ year: today.year(), month: today.month() + 1 })
  const [selectedDay, setSelectedDay] = useState<string | null>(today.format("YYYYMMDD"))
  const [selectedSections, setSelectedSections] = useState<string[]>(DEFAULT_SECTIONS)

  function toggleSection(s: string) {
    setSelectedSections((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    )
  }

  const qc = useQueryClient()
  const { data, isLoading, error } = useBoletinCalendar(current.year, current.month, jurisdiccionId)
  const triggerMonth = useTriggerMonth()

  const { updateDocumentState, setDocumentCompleted, setDocumentFailed } = usePipelineStore()

  // Handle pipeline events: update store for live UI + invalidate query when needed
  const handleWsEvent = useCallback(
    (event: WebSocketEvent) => {
      const d = event.data as Record<string, unknown>
      switch (event.event_type) {
        case "pipeline.document.started":
          // Nuevo boletin_id asignado → refrescar para que secciones tengan el ID
          qc.invalidateQueries({ queryKey: ["boletin-calendar"] })
          break
        case "pipeline.document.stage":
          updateDocumentState(
            d.boletin_id as number,
            d.filename as string,
            d.stage as string,
            d.details as Record<string, unknown> | undefined,
          )
          break
        case "pipeline.document.completed":
          setDocumentCompleted(d.boletin_id as number)
          qc.invalidateQueries({ queryKey: ["boletin-calendar"] })
          break
        case "pipeline.document.failed":
          setDocumentFailed(
            d.boletin_id as number,
            d.filename as string,
            d.error as string,
            "unknown",
          )
          qc.invalidateQueries({ queryKey: ["boletin-calendar"] })
          break
        case "pipeline.completed":
          qc.invalidateQueries({ queryKey: ["boletin-calendar"] })
          break
      }
    },
    [updateDocumentState, setDocumentCompleted, setDocumentFailed, qc],
  )

  useWebSocket({
    eventTypes: [
      "pipeline.document.started",
      "pipeline.document.stage",
      "pipeline.document.completed",
      "pipeline.document.failed",
      "pipeline.completed",
    ],
    onEvent: handleWsEvent,
  })

  const prevMonth = () => {
    setCurrent((c) => {
      const d = dayjs(`${c.year}-${c.month}-01`).subtract(1, "month")
      return { year: d.year(), month: d.month() + 1 }
    })
    setSelectedDay(null)
  }

  const nextMonth = () => {
    setCurrent((c) => {
      const d = dayjs(`${c.year}-${c.month}-01`).add(1, "month")
      return { year: d.year(), month: d.month() + 1 }
    })
    setSelectedDay(null)
  }

  const weekdays = getWeekdays(current.year, current.month)
  const weeks = groupByWeek(weekdays)
  const todayStr = today.format("YYYYMMDD")
  const monthLabel = dayjs(`${current.year}-${String(current.month).padStart(2, "0")}-01`).format("MMMM YYYY")

  // Use the first jurisdiccion from response (or the requested one)
  const jurisdiccion = data?.jurisdicciones[0]

  return (
    <div className="space-y-4">
      {/* Month Navigator */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={prevMonth}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-sm font-semibold capitalize">{monthLabel}</span>
        <div className="flex items-center gap-1">
          {jurisdiccionId && (
            <>
              {ALL_SECTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => toggleSection(s)}
                  className={`h-7 px-2 text-xs rounded border transition-colors ${
                    selectedSections.includes(s)
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-background text-muted-foreground border-border hover:border-primary/60"
                  }`}
                >
                  {SECTION_SHORT[s]}
                </button>
              ))}
              <Button
                variant="outline"
                size="sm"
                className="text-xs h-7"
                disabled={triggerMonth.isPending || selectedSections.length === 0}
                onClick={() =>
                  triggerMonth.mutate({
                    jurisdiccion_id: jurisdiccionId,
                    year: current.year,
                    month: current.month,
                    sections: selectedSections,
                  })
                }
              >
                {triggerMonth.isPending ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                Procesar mes
              </Button>
            </>
          )}
          <Button variant="ghost" size="sm" onClick={nextMonth} disabled={current.year === today.year() && current.month >= today.month() + 1}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Status legend */}
      <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
        {Object.entries(STATUS_STYLE).map(([key, s]) => (
          <div key={key} className="flex items-center gap-1">
            <span className={dotClass(key)} />
            {s.label}
          </div>
        ))}
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-8 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />
          Cargando...
        </div>
      )}

      {error && (
        <p className="text-sm text-destructive">Error cargando el calendario.</p>
      )}

      {!isLoading && !error && (
        <>
          {/* Column headers: Mon–Fri */}
          <div className="grid grid-cols-5 gap-1 text-xs font-medium text-muted-foreground text-center">
            {["Lun", "Mar", "Mié", "Jue", "Vie"].map((d) => (
              <div key={d}>{d}</div>
            ))}
          </div>

          {/* Calendar grid */}
          {weeks.map((week, wi) => {
            // Pad week to 5 cells
            const cells: (string | null)[] = Array(5).fill(null)
            for (const d of week) {
              const dow = dayjs(d, "YYYYMMDD").day() // 0=Sun … 6=Sat
              const col = dow === 0 ? 4 : dow - 1   // Mon=0 … Fri=4
              cells[col] = d
            }

            return (
              <div key={wi} className="grid grid-cols-5 gap-1">
                {cells.map((dateStr, ci) =>
                  dateStr ? (
                    <DayCell
                      key={dateStr}
                      dateStr={dateStr}
                      secciones={jurisdiccion?.dias[dateStr]?.secciones}
                      isToday={dateStr === todayStr}
                      isSelected={dateStr === selectedDay}
                      isFuture={dateStr > todayStr}
                      onClick={() => setSelectedDay(dateStr === selectedDay ? null : dateStr)}
                    />
                  ) : (
                    <div key={ci} />
                  )
                )}
              </div>
            )
          })}

          {/* Day detail panel */}
          {selectedDay && jurisdiccion && (
            <DayDetailPanel dateStr={selectedDay} jurisdiccion={jurisdiccion} isFuture={selectedDay > todayStr} />
          )}

          {data && data.jurisdicciones.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-6">
              No hay datos para este mes.
            </p>
          )}
        </>
      )}
    </div>
  )
}
