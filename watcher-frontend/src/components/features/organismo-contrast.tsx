import { AlertTriangle } from "lucide-react"
import { cn } from "@/lib/utils"
import type { OrgResumenItem, SerieGasto } from "@/types/presupuesto"
import { barWidth, formatARS, formatPct, asMoney } from "@/lib/presupuesto-format"

function PctBar({
  pct,
  over,
  tone,
}: {
  pct: number | null
  over: boolean
  tone: "compromiso" | "ejecucion"
}) {
  const fill =
    over ? "bg-red-500/80" : tone === "compromiso" ? "bg-amber-500/70" : "bg-blue-500/70"
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-muted rounded h-3 overflow-hidden">
        <div className={cn("h-full rounded", fill)} style={{ width: `${barWidth(pct)}%` }} />
      </div>
      <span
        className={cn(
          "text-xs font-mono w-14 text-right shrink-0",
          over ? "text-red-400 font-semibold" : "text-muted-foreground"
        )}
      >
        {formatPct(pct)}
      </span>
    </div>
  )
}

export function OrganismoContrastList({
  items,
  serie,
}: {
  items: OrgResumenItem[]
  serie: SerieGasto
}) {
  const matched = (items ?? []).filter((item) => item.matched)
  const sorted = [...matched].sort((a, b) => {
    const av = asMoney(serie === "compromiso" ? a.monto_compromiso : a.monto_ejecucion) ?? 0
    const bv = asMoney(serie === "compromiso" ? b.monto_compromiso : b.monto_ejecucion) ?? 0
    return bv - av
  })
  const visible = sorted.slice(0, 12)

  if (visible.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Ningún organismo matcheado contra el presupuesto vigente. Los actos
        municipales y los sin partida no tienen denominador.
      </p>
    )
  }

  return (
    <div className="space-y-4">
      {visible.map((item) => {
        const over =
          serie === "compromiso" ? item.sobre_compromiso : item.sobre_ejecucion
        return (
          <div key={item.organismo ?? "sin"} className="space-y-1.5">
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="truncate font-medium pr-2">
                {item.organismo ?? "(sin organismo)"}
              </span>
              <div className="flex items-center gap-3 shrink-0 text-xs text-muted-foreground">
                {over && (
                  <span className="inline-flex items-center gap-1 text-red-400">
                    <AlertTriangle className="h-3 w-3" />
                    &gt;100%
                  </span>
                )}
                <span>{item.count} actos</span>
                <span className="font-mono text-foreground">
                  {formatARS(
                    serie === "compromiso"
                      ? item.monto_compromiso
                      : item.monto_ejecucion
                  )}
                  {" / "}
                  {formatARS(item.monto_vigente)}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-[4.5rem_1fr] gap-x-3 gap-y-1">
              <span className="text-[11px] uppercase tracking-wide text-amber-500/90 self-center">
                Compromiso
              </span>
              <PctBar
                pct={item.pct_compromiso}
                over={item.sobre_compromiso}
                tone="compromiso"
              />
              <span className="text-[11px] uppercase tracking-wide text-blue-400/90 self-center">
                Ejecución
              </span>
              <PctBar
                pct={item.pct_ejecucion}
                over={item.sobre_ejecucion}
                tone="ejecucion"
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
