import { AlertTriangle, Info, ShieldAlert } from "lucide-react"
import { cn } from "@/lib/utils"
import type { EtapaProxyBoResumen, ProxyBoResumen } from "@/types/presupuesto"
import { barWidth, formatARS, formatPct } from "@/lib/presupuesto-format"

/**
 * Proxy BO por finalidad (Should de Ampliación B).
 *
 * Lo que el Boletín Oficial **publica** — llamado, adjudicación, contrato, pago —
 * atribuido a los programas de cada finalidad, contra el techo de esa finalidad.
 *
 * Reglas duras:
 *
 * - **Nunca "Devengado".** El rótulo sale de `honestidad.etiqueta_numerador`
 *   ("publicado en el BO"), que viene del backend, y los flags `es_devengado` /
 *   `es_devengado_cge` son `False`. Un acto publicado no devenga gasto.
 * - **Panel separado del contraste de barras.** No entra en el cociente de
 *   "Compromiso" ni de "Ejecución": es otro numerador, con otro rótulo.
 * - **La composición se informa, no se resta.** En el corte feb–sep 2026 el proxy
 *   es 99,35% llamado, así que mostrar un único número sin las etapas repetiría el
 *   error que V.3.3 arregló en la barra de "Compromiso".
 */
export function ProxyBoPanel({
  data,
  error,
}: {
  data?: ProxyBoResumen
  error?: Error | null
}) {
  if (error) return <HuecoDeclarado error={error} />
  if (!data) return null

  const etiqueta = data.honestidad.etiqueta_numerador
  const cobertura = data.cobertura
  const sinPrograma = cobertura.pct_sin_programa ?? 0
  const conPrograma = Math.max(0, 100 - sinPrograma)

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-muted-foreground">
            Publicado en el BO por finalidad, contra el techo de esa finalidad
          </p>
          <p className="text-2xl font-bold font-mono">
            {formatARS(cobertura.monto_total)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            {cobertura.fecha_desde && cobertura.fecha_hasta
              ? `${cobertura.fecha_desde} → ${cobertura.fecha_hasta}`
              : "sin actos publicados en el ejercicio"}{" "}
            · ejercicio {data.ejercicio}
          </p>
        </div>
        {/* El rótulo del numerador se lee de la respuesta: no se elige acá. */}
        <span className="inline-flex items-center gap-2 rounded-md border border-zinc-500/40 bg-zinc-500/10 px-3 py-1.5 text-xs text-zinc-300">
          {etiqueta}
        </span>
      </div>

      <CoberturaBanner
        cobertura={cobertura}
        conPrograma={conPrograma}
        sinPrograma={sinPrograma}
      />

      <div className="space-y-4">
        {data.items.map((item) => (
          <div key={item.clave} className="space-y-1.5">
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="truncate font-medium pr-2">{item.label}</span>
              <div className="flex items-center gap-3 shrink-0 text-xs text-muted-foreground">
                {item.pct_publicado_techo != null && item.pct_publicado_techo > 100 && (
                  <span className="inline-flex items-center gap-1 text-red-400">
                    <AlertTriangle className="h-3 w-3" />
                    &gt;100%
                  </span>
                )}
                <span>{item.count.toLocaleString("es-AR")} actos</span>
                <span className="font-mono text-foreground">
                  {formatARS(item.monto_publicado)}
                  {" / "}
                  {formatARS(item.monto_techo)}
                </span>
                <span className="font-mono w-16 text-right text-foreground">
                  {item.pct_publicado_techo == null
                    ? "sin techo"
                    : formatPct(item.pct_publicado_techo)}
                </span>
              </div>
            </div>
            <div className="flex-1 bg-muted rounded h-3 overflow-hidden">
              <div
                className={cn(
                  "h-full rounded",
                  item.pct_publicado_techo != null && item.pct_publicado_techo > 100
                    ? "bg-red-500/80"
                    : item.clave === "sin_clasificar"
                      ? "bg-zinc-500/60"
                      : "bg-emerald-500/60"
                )}
                style={{ width: `${barWidth(item.pct_publicado_techo)}%` }}
              />
            </div>
            {item.detalle?.length > 0 && (
              <div className="mt-2 rounded-md border border-border/60 bg-muted/30 p-3 space-y-2">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Info className="h-3.5 w-3.5 shrink-0" />
                  Qué hay adentro de "sin clasificar"
                </div>
                <div className="divide-y divide-border/60">
                  {item.detalle.map((componente) => (
                    <div
                      key={componente.clave}
                      className="flex items-center justify-between gap-3 py-1.5 text-xs"
                    >
                      <span className="truncate pr-2 text-muted-foreground">
                        {/* `label: null` cae a la clave: el `6` del anexo no tiene
                            nombre en el clasificador. */}
                        {componente.label ?? componente.clave}
                      </span>
                      <div className="flex items-center gap-3 shrink-0 text-muted-foreground">
                        <span className="font-mono text-foreground">
                          {formatARS(componente.monto_publicado)}
                          {" / "}
                          {formatARS(componente.monto_techo)}
                        </span>
                        <span className="font-mono w-16 text-right">
                          {componente.pct_publicado_techo == null
                            ? "sin techo"
                            : formatPct(componente.pct_publicado_techo)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <ComposicionEtapas etapas={data.etapas} />

      <Honestidad notas={data.honestidad.notas} />
    </div>
  )
}

function CoberturaBanner({
  cobertura,
  conPrograma,
  sinPrograma,
}: {
  cobertura: ProxyBoResumen["cobertura"]
  conPrograma: number
  sinPrograma: number
}) {
  return (
    <div className="rounded-lg border border-border bg-muted/40 p-4 space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 text-sm font-medium">
          <Info className="h-4 w-4 text-muted-foreground" />
          Cobertura del proxy
        </span>
        <span className="text-xs font-mono text-muted-foreground">
          {formatARS(cobertura.monto_sin_programa)} sin programa
        </span>
      </div>
      <div className="flex h-3 rounded overflow-hidden bg-muted">
        <div className="h-full bg-emerald-500/50" style={{ width: `${conPrograma}%` }} />
        <div className="h-full bg-zinc-500/50" style={{ width: `${sinPrograma}%` }} />
      </div>
      <p className="text-xs text-muted-foreground">
        <span className="font-mono text-foreground">{formatPct(conPrograma)}</span> del
        publicado se pudo atribuir a un programa del ejercicio.{" "}
        <span className="font-mono text-foreground">{formatPct(sinPrograma)}</span> (
        {formatARS(cobertura.monto_sin_programa)}, {cobertura.count_sin_programa} actos)
        no: son actos sin programa identificable en el presupuesto vigente.{" "}
        <span className="text-foreground">
          No se reparten entre las finalidades
        </span>{" "}
        — repartirlos inventaría una atribución que el boletín no publica.
      </p>
      {cobertura.denominador_es_anual && (
        <p className="text-xs text-muted-foreground">
          El % de cada finalidad divide contra la{" "}
          <span className="text-foreground">Ley anual completa</span>, mientras el
          numerador cubre el período publicado
          {cobertura.fecha_desde && cobertura.fecha_hasta
            ? ` (${cobertura.fecha_desde} → ${cobertura.fecha_hasta})`
            : ""}
          : los dos lados no cubren el mismo período, así que el % subestima el avance
          del año. No se prorratea la Ley.
        </p>
      )}
      {cobertura.monto_total !== cobertura.monto_con_programa && (
        <p className="text-xs text-muted-foreground">
          Dentro de lo atribuido:{" "}
          <span className="font-mono text-foreground">
            {formatARS(cobertura.monto_atribuido_finalidad)}
          </span>{" "}
          cae en una finalidad del clasificador y{" "}
          <span className="font-mono text-foreground">
            {formatARS(cobertura.monto_no_clasificado)}
          </span>{" "}
          en ruido de partida del anexo — no es un agujero, es un rótulo de la fuente.
        </p>
      )}
    </div>
  )
}

/**
 * La composición del proxy por etapa.  Se muestra aparte y no se resta de nada:
 * el 99,35% del publicado del corte es llamado a licitación, y un único número
 * "publicado" sin esto sobreafirmaría el compromiso.
 */
function ComposicionEtapas({ etapas }: { etapas: EtapaProxyBoResumen[] }) {
  const total = etapas.reduce((acc, e) => acc + (Number(e.monto) || 0), 0)
  if (!etapas?.length) return null
  return (
    <div className="space-y-2">
      <span className="text-sm font-medium text-muted-foreground">
        Composición: en qué etapa del gasto está lo publicado
      </span>
      <div className="divide-y divide-border/60">
        {etapas.map((etapa) => {
          const pct = total > 0 ? (100 * (Number(etapa.monto) || 0)) / total : 0
          return (
            <div key={etapa.clave} className="flex items-center gap-3 py-1.5 text-xs">
              <span className="w-64 shrink-0 truncate text-muted-foreground">
                {etapa.label}
              </span>
              <div className="flex-1 bg-muted rounded h-2.5 overflow-hidden">
                <div
                  className="h-full bg-amber-500/60 rounded"
                  style={{ width: `${barWidth(pct)}%` }}
                />
              </div>
              <span className="font-mono w-24 text-right shrink-0 text-foreground">
                {formatARS(etapa.monto)}
              </span>
              <span className="font-mono w-14 text-right shrink-0 text-muted-foreground">
                {formatPct(pct)}
              </span>
            </div>
          )
        })}
      </div>
      <p className="text-xs text-muted-foreground">
        Un llamado a licitación publicado no es un compromiso asumido. Las etapas se
        informan por separado y no se restan del total: restarlas movería el umbral
        de las alertas.
      </p>
    </div>
  )
}

function Honestidad({ notas }: { notas: string[] }) {
  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium">
        <ShieldAlert className="h-4 w-4 text-amber-500/80" />
        Esto no es ejecución presupuestaria
      </div>
      <ul className="space-y-1 text-xs text-muted-foreground list-disc pl-4">
        {notas.map((nota) => (
          <li key={nota}>{nota}</li>
        ))}
      </ul>
    </div>
  )
}

/** El 404 es el hueco: sin Ley cargada no hay techo contra el que contrastar. */
function HuecoDeclarado({ error }: { error: Error }) {
  return (
    <div className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium">
        <AlertTriangle className="h-4 w-4 text-amber-500" />
        Sin techo declarado para este ejercicio
      </div>
      <p className="text-xs text-muted-foreground">
        {error.message || "No se pudo leer el techo de la Ley/Mapas."}
      </p>
      <p className="text-xs text-muted-foreground">
        El proxy no se puede calcular sin el techo de la Ley: no es un $0 publicado,
        es un hueco.
      </p>
    </div>
  )
}
