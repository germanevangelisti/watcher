import { AlertTriangle, CalendarClock, Info } from "lucide-react"
import { cn } from "@/lib/utils"
import type {
  CoberturaResumen,
  CoberturaTemporalResumen,
  DenominadorSinDuenoResumen,
  OrgResumenItem,
  SerieGasto,
} from "@/types/presupuesto"
import {
  barWidth,
  formatARS,
  formatPct,
  asMoney,
  parseMoney,
} from "@/lib/presupuesto-format"

const MAX_VISIBLES = 12

const MESES = [
  "ene",
  "feb",
  "mar",
  "abr",
  "may",
  "jun",
  "jul",
  "ago",
  "sep",
  "oct",
  "nov",
  "dic",
]

/** "2026-05" → "may". Falls back to the raw value rather than inventing one. */
function mesCorto(ym: string): string {
  const m = Number(ym.slice(5, 7))
  return MESES[m - 1] ?? ym
}

function pctOf(
  numerador: number | string | null | undefined,
  vigente: number | string | null | undefined
): number | null {
  const n = parseMoney(numerador)
  const v = parseMoney(vigente)
  if (n == null || v == null || v <= 0) return null
  return (100 * n) / v
}

function PctBar({
  pct,
  over,
  tone,
}: {
  pct: number | null
  over: boolean
  tone: "publicado" | "comprometido" | "ejecucion"
}) {
  const fill =
    over
      ? "bg-red-500/80"
      : tone === "publicado"
        ? "bg-amber-500/40"
        : tone === "comprometido"
          ? "bg-amber-500/80"
          : "bg-blue-500/70"
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

function CoberturaTemporalBanner({
  temporal,
}: {
  temporal: CoberturaTemporalResumen
}) {
  const { meses_cubiertos, meses_del_ejercicio } = temporal
  const rango =
    temporal.mes_desde && temporal.mes_hasta
      ? `${mesCorto(temporal.mes_desde)}–${mesCorto(temporal.mes_hasta)} ${temporal.mes_desde.slice(0, 4)}`
      : "sin período"
  const faltan = temporal.meses_vencidos_sin_ingesta
  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 text-sm font-medium">
          <CalendarClock className="h-4 w-4 text-amber-500/80" />
          Período del gasto medido
        </span>
        <span className="text-xs font-mono text-muted-foreground">
          {meses_cubiertos} de {meses_del_ejercicio} meses
        </span>
      </div>
      <div className="flex h-3 rounded overflow-hidden bg-muted">
        <div
          className="h-full bg-amber-500/50"
          style={{ width: `${(100 * meses_cubiertos) / meses_del_ejercicio}%` }}
        />
      </div>
      <p className="text-xs text-muted-foreground">
        El gasto medido cubre <span className="text-foreground">{rango}</span> (
        {meses_cubiertos} de {meses_del_ejercicio} meses del ejercicio), pero el
        porcentaje se calcula{" "}
        <span className="text-foreground">contra la Ley anual completa</span>. Los dos
        lados del cociente no cubren el mismo período, así que el %{" "}
        <span className="text-foreground">subestima</span> el avance del año. No se
        prorratea el presupuesto: la ejecución no es pareja mes a mes, y prorratear
        sería inventar un denominador.
      </p>
      {faltan.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Meses ya transcurridos sin ingerir ({faltan.length}):{" "}
          <span className="font-mono text-foreground">
            {faltan.map(mesCorto).join(", ")}
          </span>
          . Mientras falten, el gasto medido es un piso, no el total del año.
        </p>
      )}
      {temporal.dias_faltantes === 0 && temporal.dias_con_publicacion > 0 && (
        <p className="text-xs text-muted-foreground">
          Dentro del período no falta ningún día:{" "}
          <span className="font-mono text-foreground">
            {temporal.dias_con_publicacion}
          </span>{" "}
          días con publicación
          {temporal.dias_justificados > 0 && (
            <>
              {" + "}
              <span className="font-mono text-foreground">
                {temporal.dias_justificados}
              </span>{" "}
              feriados en que el boletín no salió (justificados)
            </>
          )}
          , 0 días sin explicación.
        </p>
      )}
      {temporal.dias_faltantes > 0 && (
        <p className="text-xs text-red-400">
          {temporal.dias_faltantes} día(s) del período fallaron sin justificación: ese
          gasto falta y no está declarado en ningún otro lado.
        </p>
      )}
    </div>
  )
}

function DenominadorSinDuenoBanner({
  denominador,
}: {
  denominador: DenominadorSinDuenoResumen
}) {
  const pct = denominador.pct_sin_dueno ?? 0
  return (
    <div className="rounded-lg border border-border bg-muted/40 p-4 space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 text-sm font-medium">
          <Info className="h-4 w-4 text-muted-foreground" />
          Techo de la Ley
        </span>
        <span className="text-xs font-mono text-muted-foreground">
          {formatPct(pct)} sin organismo
        </span>
      </div>
      <div className="flex h-3 rounded overflow-hidden bg-muted">
        <div
          className="h-full bg-emerald-500/50"
          style={{ width: `${Math.max(0, 100 - pct)}%` }}
        />
        <div className="h-full bg-zinc-500/50" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-muted-foreground">
        De los <span className="font-mono text-foreground">{formatARS(denominador.monto_total)}</span>{" "}
        de la Ley, <span className="font-mono text-foreground">{formatARS(denominador.monto_sin_dueno)}</span>{" "}
        ({denominador.count_sin_dueno} programas) tienen el organismo truncado en la
        fuente. El matcher no puede asignarlos a nadie, así que ese presupuesto{" "}
        <span className="text-foreground">nunca puede ser el techo de un gasto</span>.
        No se resta del denominador: el % que ves lo sigue dividiendo la Ley completa,
        y restarlo movería todos los % a la vez. Pero el techo verificado es{" "}
        <span className="font-mono text-foreground">
          {formatARS(denominador.monto_verificable)}
        </span>
        , no el total. Recuperar esos nombres es trabajo sobre el parseo de los Mapas,
        no sobre el contraste.
      </p>
      <div className="divide-y divide-border/60">
        {denominador.por_organismo.slice(0, MAX_VISIBLES).map((item) => (
          <div
            key={item.organismo}
            className="flex items-center justify-between gap-3 py-1.5 text-sm"
          >
            <span className="truncate pr-2 text-muted-foreground">
              {item.organismo}
            </span>
            <div className="flex items-center gap-3 shrink-0 text-xs text-muted-foreground">
              <span>{item.count} programas</span>
              <span className="font-mono text-foreground">
                {formatARS(item.monto_vigente)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function CoberturaBanner({ cobertura }: { cobertura: CoberturaResumen }) {
  const sinPct = cobertura.pct_sin_denominador ?? 0
  const conPct = Math.max(0, 100 - sinPct)
  return (
    <div className="rounded-lg border border-border bg-muted/40 p-4 space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 text-sm font-medium">
          <Info className="h-4 w-4 text-muted-foreground" />
          Cobertura del contraste
        </span>
        <span className="text-xs font-mono text-muted-foreground">
          {formatARS(cobertura.monto_sin_denominador)} sin techo
        </span>
      </div>
      <div className="flex h-3 rounded overflow-hidden bg-muted">
        <div className="h-full bg-emerald-500/50" style={{ width: `${conPct}%` }} />
        <div className="h-full bg-zinc-500/50" style={{ width: `${sinPct}%` }} />
      </div>
      <p className="text-xs text-muted-foreground">
        <span className="font-mono text-foreground">{formatPct(conPct)}</span> del gasto
        medido tiene un denominador en la Ley.{" "}
        <span className="font-mono text-foreground">{formatPct(sinPct)}</span> (
        {formatARS(cobertura.monto_sin_denominador)},{" "}
        {cobertura.count_sin_denominador} actos) no lo tiene: es gasto publicado sin
        partida comparable en el presupuesto vigente. No se le inventa un techo ni se
        lo esconde — se declara acá y se lista abajo.
      </p>
    </div>
  )
}

function SinDenominadorList({ items }: { items: OrgResumenItem[] }) {
  const total = items.reduce(
    (acc, item) => acc + (parseMoney(item.monto_total) ?? 0),
    0
  )
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-muted-foreground">
          Sin denominador ({items.length})
        </span>
        <span className="text-xs font-mono text-muted-foreground">
          {formatARS(total)} total
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        No hay organismo equivalente en el presupuesto vigente, así que no se puede
        afirmar un %. El monto es lo publicado en el boletín.
      </p>
      <div className="divide-y divide-border/60">
        {items.slice(0, MAX_VISIBLES).map((item) => (
          <div
            key={item.organismo ?? "sin"}
            className="flex items-center justify-between gap-3 py-1.5 text-sm"
          >
            <span className="truncate pr-2 text-muted-foreground">
              {item.organismo ?? "(sin organismo)"}
            </span>
            <div className="flex items-center gap-3 shrink-0 text-xs text-muted-foreground">
              <span>{item.count} actos</span>
              <span className="font-mono text-foreground">
                {formatARS(item.monto_total)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function OrganismoContrastList({
  items,
  serie,
  cobertura,
  temporal,
  denominador,
}: {
  items: OrgResumenItem[]
  serie: SerieGasto
  cobertura?: CoberturaResumen
  temporal?: CoberturaTemporalResumen
  denominador?: DenominadorSinDuenoResumen
}) {
  const all = items ?? []
  const conDenominador = all.filter((item) => item.matched)
  const sinDenominador = all.filter((item) => !item.matched)

  const value = (item: OrgResumenItem) =>
    asMoney(serie === "compromiso" ? item.monto_compromiso : item.monto_ejecucion) ?? 0
  const sorted = [...conDenominador].sort((a, b) => value(b) - value(a))
  const visible = sorted.slice(0, MAX_VISIBLES)
  const sinSorted = [...sinDenominador].sort(
    (a, b) => (asMoney(b.monto_total) ?? 0) - (asMoney(a.monto_total) ?? 0)
  )

  return (
    <div className="space-y-5">
      {temporal && <CoberturaTemporalBanner temporal={temporal} />}
      {cobertura && <CoberturaBanner cobertura={cobertura} />}
      {denominador && <DenominadorSinDuenoBanner denominador={denominador} />}

      {visible.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Ningún organismo tiene denominador en el presupuesto vigente, así que no
          hay ningún % que mostrar. El gasto medido está listado abajo.
        </p>
      ) : (
        <div className="space-y-4">
          {visible.map((item) => {
            const over =
              serie === "compromiso" ? item.sobre_compromiso : item.sobre_ejecucion
            const comprometido =
              (parseMoney(item.monto_compromiso) ?? 0) -
              (parseMoney(item.monto_llamado) ?? 0)
            const pctComprometido = pctOf(comprometido, item.monto_vigente)
            const llamado = parseMoney(item.monto_llamado) ?? 0
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
                <div className="grid grid-cols-1 sm:grid-cols-[6.5rem_1fr] gap-x-3 gap-y-1">
                  <span className="text-[11px] uppercase tracking-wide text-amber-500/60 self-center">
                    Publicado
                  </span>
                  <PctBar
                    pct={item.pct_compromiso}
                    over={item.sobre_compromiso}
                    tone="publicado"
                  />
                  <span className="text-[11px] uppercase tracking-wide text-amber-500/90 self-center">
                    Comprometido
                  </span>
                  <PctBar
                    pct={pctComprometido}
                    over={false}
                    tone="comprometido"
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
                <p className="text-[11px] text-muted-foreground sm:pl-[7.25rem]">
                  Publicado = llamado + adjudicación + contrato. De ese total,{" "}
                  <span className="font-mono">{formatARS(item.monto_llamado)}</span> es
                  sólo <span className="text-amber-500/90">llamado</span> (intención de
                  licitar): el compromiso asumido es{" "}
                  <span className="font-mono">{formatARS(comprometido)}</span>
                  {llamado > 0 && comprometido === 0 && " — hoy no hay ninguno publicado"}
                  .
                </p>
              </div>
            )
          })}
        </div>
      )}

      {sinSorted.length > 0 && <SinDenominadorList items={sinSorted} />}
    </div>
  )
}
