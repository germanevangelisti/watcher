import { AlertTriangle, Info, Scale, ShieldAlert } from "lucide-react"
import { cn } from "@/lib/utils"
import type { FinalidadDetalleItem, FinalidadesResumen } from "@/types/presupuesto"
import { barWidth, formatARS, formatPct } from "@/lib/presupuesto-format"

/**
 * Techo de la Ley 11.088 / Mapas por finalidad (Must de Ampliación B).
 *
 * Tres cosas que esta card no hace, y que por eso se ven en pantalla y no sólo en
 * este comentario:
 *
 * 1. **No colapsa `sin_clasificar`.** En el corte 2026 ese bucket es 57,19% del
 *    techo (Servicios Económicos es la línea más grande de la Ley). Mostrar sólo
 *    1/2/3 dejaría el 42,81% restante leyéndose como el total, así que el bucket
 *    va al mismo nivel y con su `detalle[]` a la vista.
 * 2. **No inventa un "inicial ≠ vigente".** El titular sale de
 *    `honestidad.inicial_es_vigente`, que el backend **mide** fila por fila. El
 *    copy textual de `notas[]` va abajo, tal cual, para que las dos redacciones
 *    (el titular derivado del flag y la nota cruda) se vean juntas en vez de
 *    despegarse.
 * 3. **No muestra "ejecución".** El único monto acá es techo. No hay `% ejecutado`
 *    porque no hay ejecución en este endpoint: eso es el contraste del BO, más abajo.
 */
export function FinalidadesTechoCard({
  data,
  error,
}: {
  data?: FinalidadesResumen
  error?: Error | null
}) {
  if (error) return <HuecoDeclarado error={error} />
  if (!data) return null

  const items = data.items ?? []
  const bucket = items.find((item) => item.clave === "sin_clasificar")
  const filas = items.filter((item) => item.clave !== "sin_clasificar")

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-muted-foreground">
            Techo vigente del ejercicio, en mil millones de pesos
          </p>
          <p className="text-2xl font-bold font-mono">
            {formatARS(data.total_vigente)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            {data.total_registros.toLocaleString("es-AR")} programas · ejercicio{" "}
            {data.ejercicio}
          </p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs text-emerald-300">
          <Scale className="h-3.5 w-3.5" />
          Es techo, no ejecución
        </span>
      </div>

      <div className="space-y-4">
        {filas.map((item) => (
          <FinalidadRow key={item.clave} item={item} />
        ))}
        {bucket && <FinalidadRow item={bucket} detalleVisible />}
      </div>

      <Disclaimer honestidad={data.honestidad} />
    </div>
  )
}

function FinalidadRow({
  item,
  detalleVisible = false,
}: {
  item: FinalidadesResumen["items"][number]
  detalleVisible?: boolean
}) {
  const pct = item.participacion_techo_pct ?? 0
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="truncate font-medium pr-2">{item.label}</span>
        <div className="flex items-center gap-3 shrink-0 text-xs text-muted-foreground">
          <span>{item.count.toLocaleString("es-AR")} programas</span>
          <span className="font-mono text-foreground">
            {formatARS(item.monto_vigente)}
          </span>
          <span className="font-mono w-16 text-right text-foreground">
            {formatPct(pct)}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1 bg-muted rounded h-3 overflow-hidden">
          <div
            className={cn(
              "h-full rounded",
              item.clave === "sin_clasificar" ? "bg-zinc-500/60" : "bg-emerald-500/60"
            )}
            style={{ width: `${barWidth(pct)}%` }}
          />
        </div>
      </div>
      {detalleVisible && item.detalle?.length > 0 && (
        <DetalleBucket detalle={item.detalle} />
      )}
    </div>
  )
}

/**
 * El detalle del bucket, siempre visible: sin esto, "sin clasificar 57,19%" no
 * dice que 40,71 puntos de esos son Servicios Económicos.
 */
function DetalleBucket({ detalle }: { detalle: FinalidadDetalleItem[] }) {
  return (
    <div className="mt-2 rounded-md border border-border/60 bg-muted/30 p-3 space-y-2">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Info className="h-3.5 w-3.5 shrink-0" />
        Qué hay adentro de "sin clasificar"
      </div>
      <div className="divide-y divide-border/60">
        {detalle.map((componente) => (
          <div
            key={componente.clave}
            className="flex items-center justify-between gap-3 py-1.5 text-xs"
          >
            <span className="truncate pr-2 text-muted-foreground">
              {/* `label: null` cae a la clave: el `6` del anexo no tiene nombre
                  en el clasificador y mostrarlo vacío sería esconderlo. */}
              {componente.label ?? componente.clave}
            </span>
            <div className="flex items-center gap-3 shrink-0 text-muted-foreground">
              <span className="font-mono text-foreground">
                {formatARS(componente.monto_vigente)}
              </span>
              <span className="font-mono w-16 text-right">
                {formatPct(componente.participacion_techo_pct)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function Disclaimer({
  honestidad,
}: {
  honestidad: FinalidadesResumen["honestidad"]
}) {
  const { inicial_es_vigente, filas_inicial_distinto_vigente } = honestidad
  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium">
        <ShieldAlert className="h-4 w-4 text-amber-500/80" />
        Qué es y qué no es esta cifra
      </div>
      {/* Titular derivado del flag medido, no del copy: si el corte cambia, esto
          cambia solo. Abajo van las `notas[]` textuales — las dos redacciones
          quedan a la vista en vez de despegarse. */}
      <p className="text-sm text-foreground">
        {inicial_es_vigente ? (
          <>
            <span className="font-medium">Inicial = vigente</span> en todo el
            corte (0 de las filas difieren): no hay crédito modificado que
            mostrar todavía.
          </>
        ) : (
          <>
            <span className="font-medium">
              Inicial ≠ vigente en {filas_inicial_distinto_vigente} fila
              {filas_inicial_distinto_vigente === 1 ? "" : "s"}
            </span>{" "}
            de este corte: lo sancionado y lo vigente ya no coinciden, así que la
            cifra de la izquierda es lo sancionado y la de la derecha lo vigente.
          </>
        )}
      </p>
      <ul className="space-y-1 text-xs text-muted-foreground list-disc pl-4">
        {honestidad.notas.map((nota) => (
          <li key={nota}>{nota}</li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">
        No es crédito modificado · no incluye Devengado CGE
        {honestidad.es_credito_modificado || honestidad.incluye_devengado_cge
          ? " (el corte dice lo contrario: revisar la nota de arriba)"
          : ""}
        .
      </p>
    </div>
  )
}

/**
 * El 404 del backend es un dato, no un error de red: significa que el ejercicio
 * no tiene Ley cargada — un hueco. Renderizarlo como ceros afirmaría un techo $0.
 */
function HuecoDeclarado({ error }: { error: Error }) {
  const detalle = error.message || ""
  return (
    <div className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium">
        <AlertTriangle className="h-4 w-4 text-amber-500" />
        Sin techo declarado para este ejercicio
      </div>
      <p className="text-xs text-muted-foreground">
        {detalle || "No se pudo leer el techo de la Ley/Mapas de este ejercicio."}
      </p>
      <p className="text-xs text-muted-foreground">
        No es un techo de $0: es un hueco. Mientras el presupuesto base de ese
        ejercicio no esté cargado no hay contra qué contrastar, y este panel no
        inventa cifras para llenarlo.
      </p>
    </div>
  )
}
