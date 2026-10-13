import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAnalizarPrecio, useGastoDetectado } from "@/lib/api"
import type {
  AgregadoRenglones,
  AnalisisPrecio,
  Clasificacion,
  GastoFiltros,
  Nivel,
  Objeto,
  RenglonAnalisis,
  TipoGasto,
} from "@/types/precio-mercado"
import {
  CLASIFICACION_LABEL,
  NIVEL_LABEL,
  OBJETO_LABEL,
  TIPO_GASTO_LABEL,
  formatArs,
} from "@/lib/precio-mercado-format"

const CLASIFICACION_STYLE: Record<Clasificacion, string> = {
  dentro_de_rango: "bg-green-500/10 text-green-400",
  observable: "bg-yellow-500/10 text-yellow-400",
  alerta: "bg-red-500/10 text-red-400",
  sin_datos_suficientes: "bg-muted text-muted-foreground",
}

function ClasificacionChip({ value }: { value: Clasificacion }) {
  return (
    <span data-testid="clasificacion" className={`rounded px-2 py-0.5 text-xs font-medium ${CLASIFICACION_STYLE[value]}`}>
      {CLASIFICACION_LABEL[value]}
    </span>
  )
}

const pct = (v: number | null) => (v != null ? `${(v * 100).toFixed(0)}%` : "-")

function AnalisisPorRenglon({ rows, agregado }: { rows: RenglonAnalisis[]; agregado?: AgregadoRenglones | null }) {
  return (
    <div data-testid="analisis-renglones">
      <h3 className="mb-1 font-medium">Análisis por renglón</h3>
      <table className="w-full text-left text-xs">
        <thead className="text-muted-foreground">
          <tr>
            <th>Renglón</th><th>Ítem</th><th>Cantidad</th><th>Precio unitario</th>
            <th>Mediana</th><th>Desvío</th><th>Clasificación</th><th>Referencias</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-border align-top" data-testid="renglon-analisis">
              <td>{r.numero ?? i + 1}</td>
              <td>{r.item}</td>
              <td>{r.cantidad != null ? `${r.cantidad} ${r.unidad}` : "-"}</td>
              <td title={r.origen_precio ?? undefined}>{r.precio_unitario != null ? formatArs(r.precio_unitario) : "solo monto total"}</td>
              <td>{formatArs(r.comparacion.mediana)}</td>
              <td>{pct(r.comparacion.desvio)}</td>
              <td><ClasificacionChip value={r.comparacion.clasificacion} /></td>
              <td>
                {r.referencias.length === 0 ? "0" : (
                  <details>
                    <summary className="cursor-pointer">{r.referencias.length}</summary>
                    <ul className="mt-1 space-y-0.5">
                      {r.referencias.map((ref, j) => (
                        <li key={j}>
                          {ref.url ? <a className="underline" href={ref.url} target="_blank" rel="noreferrer">{ref.source}</a> : ref.source}
                          {": "}{ref.description} · {formatArs(ref.unit_price)} · {ref.observed_on}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {agregado && (
        <p className="mt-2 text-xs" data-testid="agregado-renglones">
          <span className="font-medium">Agregado:</span> monto del acto {formatArs(agregado.monto_total_acto)} vs
          estimado de mercado {agregado.estimado_mercado != null ? formatArs(agregado.estimado_mercado) : "no calculable"}
          {" "}(desvío {pct(agregado.desvio)}) · <ClasificacionChip value={agregado.clasificacion} />
          {agregado.motivo && <span className="text-muted-foreground"> · {agregado.motivo}</span>}
          <span className="block text-muted-foreground">{agregado.nota}</span>
        </p>
      )}
    </div>
  )
}

function Resultado({ data }: { data: AnalisisPrecio }) {
  const { extraccion, comparacion, umbrales } = data
  return (
    <Card data-testid="resultado-analisis">
      <CardHeader>
        <CardTitle className="text-lg">{data.acto.concepto}</CardTitle>
        <CardDescription>
          {data.acto.organismo} · {data.acto.fecha} · {formatArs(data.acto.monto)}
          {data.acto.boletin_url && (
            <> · <a className="underline" href={data.acto.boletin_url} target="_blank" rel="noreferrer">Boletín oficial</a></>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="flex flex-wrap items-center gap-3">
          <ClasificacionChip value={comparacion.clasificacion} />
          {comparacion.motivo && <span className="text-muted-foreground">{comparacion.motivo}</span>}
        </div>

        <dl className="grid grid-cols-2 gap-2 md:grid-cols-4">
          <div><dt className="text-muted-foreground">Ítem</dt><dd>{extraccion.item}</dd></div>
          <div><dt className="text-muted-foreground">Cantidad</dt><dd>{extraccion.cantidad != null ? `${extraccion.cantidad} ${extraccion.unidad ?? ""}` : "no declarada"}</dd></div>
          <div><dt className="text-muted-foreground">Precio unitario</dt><dd>{formatArs(data.precio_unitario)}</dd></div>
          <div><dt className="text-muted-foreground">Mediana de referencias</dt><dd>{formatArs(comparacion.mediana)}</dd></div>
          <div><dt className="text-muted-foreground">Desvío</dt><dd>{comparacion.desvio != null ? `${(comparacion.desvio * 100).toFixed(0)}%` : "-"}</dd></div>
          <div><dt className="text-muted-foreground">Referencias</dt><dd>{comparacion.n_referencias}</dd></div>
          <div><dt className="text-muted-foreground">Extracción</dt><dd>{extraccion.metodo === "llm" ? `modelo (${data.proveedor_llm ?? "-"})` : "reglas"}</dd></div>
          <div><dt className="text-muted-foreground">Umbrales</dt><dd>&gt;{umbrales.observable * 100}% / &gt;{umbrales.alerta * 100}% · mín. {umbrales.min_references}</dd></div>
        </dl>

        {extraccion.proceso && (
          <div data-testid="proceso-compras">
            <h3 className="mb-1 font-medium">
              Proceso en ComprasCba:{" "}
              <a className="underline" href={extraccion.proceso.url} target="_blank" rel="noreferrer">{extraccion.proceso.nro}</a>
            </h3>
            <p className="text-xs text-muted-foreground">
              {extraccion.proceso.tipo} · {extraccion.proceso.servicio} · {extraccion.proceso.estado}
              {extraccion.proceso.documento && <> · renglones del pliego “{extraccion.proceso.documento}”</>}
              {extraccion.proceso.origen === "grilla" && <> · renglones publicados en el portal</>}
            </p>
            {extraccion.renglones && extraccion.renglones.length > 0 && (
              <table className="mt-1 w-full text-left text-xs" data-testid="renglones">
                <thead className="text-muted-foreground">
                  <tr><th>Renglón</th><th>Descripción</th><th>Cantidad</th><th>Precio de referencia</th></tr>
                </thead>
                <tbody>
                  {extraccion.renglones.map((r, i) => (
                    <tr key={i} className="border-t border-border">
                      <td>{r.numero ?? i + 1}</td><td>{r.descripcion}</td>
                      <td>{r.cantidad ?? "-"}</td><td>{formatArs(r.precio_referencia)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {data.renglones_analisis && data.renglones_analisis.length > 0 && (
          <AnalisisPorRenglon rows={data.renglones_analisis} agregado={data.agregado} />
        )}

        <div>
          <h3 className="mb-1 font-medium">Fuentes consultadas</h3>
          <ul className="space-y-1" data-testid="fuentes">
            {data.fuentes.map((f) => (
              <li key={f.fuente}>
                <span className="font-medium">{f.fuente}</span>: {f.disponible ? `${f.referencias} referencias` : "no disponible"}
                {f.motivo && <span className="text-muted-foreground"> - {f.motivo}</span>}
              </li>
            ))}
          </ul>
        </div>

        {data.referencias.length > 0 && (
          <table className="w-full text-left text-xs" data-testid="referencias">
            <thead className="text-muted-foreground">
              <tr><th>Fuente</th><th>Descripción</th><th>Precio unitario</th><th>Fecha</th></tr>
            </thead>
            <tbody>
              {data.referencias.map((r, i) => (
                <tr key={i} className="border-t border-border">
                  <td>{r.url ? <a className="underline" href={r.url} target="_blank" rel="noreferrer">{r.source}</a> : r.source}</td>
                  <td>{r.description}</td>
                  <td>{formatArs(r.unit_price)}</td>
                  <td>{r.observed_on}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <p className="text-xs text-muted-foreground" data-testid="aviso">{data.aviso}</p>
      </CardContent>
    </Card>
  )
}

/** El procedimiento por el que se mueve el dinero. */
const TIPOS: TipoGasto[] = [
  "licitacion",
  "concurso_precios",
  "subasta_electronica",
  "compra_directa",
  "contratacion",
  "subsidio_transferencia",
  "otro",
]

/** Qué se compra o se hace. Eje aparte: una licitación puede ser de obra o de bienes. */
const OBJETOS: Objeto[] = ["obra", "bien", "servicio", "transferencia", "otro"]

const NIVELES: Nivel[] = ["provincial", "municipal", "comunal", "nacional"]

const SELECT_CLASS =
  "mt-1 w-full rounded border border-border bg-background px-2 py-1 text-sm"

export function PrecioMercadoPage() {
  const [filtros, setFiltros] = useState<GastoFiltros>({ solo_gasto: true })
  const [selected, setSelected] = useState<number | null>(null)
  const { data, isLoading, isError } = useGastoDetectado(filtros)
  const analizar = useAnalizarPrecio()

  const set = (clave: keyof GastoFiltros, valor: string) =>
    setFiltros((f) => ({ ...f, [clave]: valor }))

  const onAnalizar = (ejecucionId: number) => {
    setSelected(ejecucionId)
    analizar.mutate(ejecucionId)
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Gasto público detectado</h1>
        <p className="mt-2 text-muted-foreground">
          Todo el gasto publicado en los boletines del corte, clasificado por tipo de gasto y nivel de
          gobierno. Elegí un acto para analizarlo en profundidad: el análisis se corre a pedido, compara
          precios contra referencias con fuente y fecha, y no emite dictamen.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-4">
        <label className="text-sm">
          <span className="text-muted-foreground">Tipo de gasto</span>
          <select
            data-testid="filtro-tipo"
            className={SELECT_CLASS}
            value={filtros.tipo ?? ""}
            onChange={(e) => set("tipo", e.target.value)}
          >
            <option value="">Todos</option>
            {TIPOS.map((t) => (
              <option key={t} value={t}>{TIPO_GASTO_LABEL[t]}</option>
            ))}
          </select>
        </label>

        <label className="text-sm">
          <span className="text-muted-foreground">Objeto</span>
          <select
            data-testid="filtro-objeto"
            className={SELECT_CLASS}
            value={filtros.objeto ?? ""}
            onChange={(e) => set("objeto", e.target.value)}
          >
            <option value="">Todos</option>
            {OBJETOS.map((o) => (
              <option key={o} value={o}>{OBJETO_LABEL[o]}</option>
            ))}
          </select>
        </label>

        <label className="text-sm">
          <span className="text-muted-foreground">Nivel</span>
          <select
            data-testid="filtro-nivel"
            className={SELECT_CLASS}
            value={filtros.nivel ?? ""}
            onChange={(e) => set("nivel", e.target.value)}
          >
            <option value="">Todos</option>
            {NIVELES.map((n) => (
              <option key={n} value={n}>{NIVEL_LABEL[n]}</option>
            ))}
          </select>
        </label>

        <label className="text-sm">
          <span className="text-muted-foreground">Organismo</span>
          <Input
            data-testid="filtro-organismo"
            className="mt-1"
            value={filtros.organismo ?? ""}
            onChange={(e) => set("organismo", e.target.value)}
          />
        </label>

        <label className="text-sm">
          <span className="text-muted-foreground">Texto</span>
          <Input
            data-testid="filtro-q"
            className="mt-1"
            placeholder="concepto u organismo"
            value={filtros.q ?? ""}
            onChange={(e) => set("q", e.target.value)}
          />
        </label>

        <label className="text-sm">
          <span className="text-muted-foreground">Publicado desde</span>
          <Input
            data-testid="filtro-desde"
            className="mt-1"
            type="date"
            value={filtros.fecha_desde ?? ""}
            onChange={(e) => set("fecha_desde", e.target.value)}
          />
        </label>

        <label className="text-sm">
          <span className="text-muted-foreground">Publicado hasta</span>
          <Input
            data-testid="filtro-hasta"
            className="mt-1"
            type="date"
            value={filtros.fecha_hasta ?? ""}
            onChange={(e) => set("fecha_hasta", e.target.value)}
          />
        </label>

        <label className="text-sm">
          <span className="text-muted-foreground">Monto mínimo</span>
          <Input
            data-testid="filtro-monto-min"
            className="mt-1"
            type="number"
            value={filtros.monto_min ?? ""}
            onChange={(e) => set("monto_min", e.target.value)}
          />
        </label>

        <label className="text-sm">
          <span className="text-muted-foreground">Monto máximo</span>
          <Input
            data-testid="filtro-monto-max"
            className="mt-1"
            type="number"
            value={filtros.monto_max ?? ""}
            onChange={(e) => set("monto_max", e.target.value)}
          />
        </label>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          data-testid="filtro-solo-gasto"
          checked={filtros.solo_gasto ?? true}
          onChange={(e) => setFiltros((f) => ({ ...f, solo_gasto: e.target.checked }))}
        />
        Ver también los actos que no son gasto (edictos judiciales, actos societarios, partidas)
      </label>

      {analizar.isPending && (
        <p className="text-sm text-muted-foreground">Analizando el acto {selected}... puede tardar con el modelo local.</p>
      )}
      {analizar.isError && <p className="text-sm text-red-400">No se pudo completar el análisis.</p>}
      {analizar.data && <Resultado data={analizar.data} />}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Gasto detectado</CardTitle>
          <CardDescription>
            {data ? (
              <span data-testid="totales">
                {data.total} actos · {formatArs(data.suma)}
              </span>
            ) : " "}
            {data && data.republicaciones_excluidas > 0 && (
              <span data-testid="republicaciones" className="mt-1 block text-xs">
                La suma no incluye {formatArs(data.republicaciones_excluidas)} de actos republicados, que sí
                están listados.
              </span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && <p className="text-sm text-muted-foreground">Cargando...</p>}
          {isError && <p className="text-sm text-red-400">No se pudo cargar la lista.</p>}
          {data && data.items.length === 0 && (
            <p className="text-sm text-muted-foreground">Sin actos para este filtro.</p>
          )}
          {data && data.items.length > 0 && (
            <table className="w-full text-left text-sm" data-testid="gasto-detectado">
              <thead className="text-muted-foreground">
                <tr>
                  <th>Fecha</th><th>Organismo</th><th>Nivel</th><th>Tipo · objeto</th>
                  <th>Concepto</th><th>Monto</th><th>Último análisis</th><th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((o) => (
                  <tr key={o.analisis_id} className="border-t border-border align-top">
                    <td className="whitespace-nowrap pr-2">{o.fecha}</td>
                    <td className="pr-2">
                      {o.organismo}
                      {o.municipio && <div className="text-xs text-muted-foreground">{o.municipio}</div>}
                    </td>
                    <td className="pr-2">{NIVEL_LABEL[o.nivel]}</td>
                    <td className="pr-2">
                      {TIPO_GASTO_LABEL[o.tipo_gasto]}
                      <div className="text-xs text-muted-foreground">{OBJETO_LABEL[o.objeto]}</div>
                    </td>
                    <td className="pr-2">
                      {o.concepto ?? o.gasto_motivo}
                      {o.concepto && (
                        <div className="text-xs text-muted-foreground">{o.gasto_motivo}</div>
                      )}
                      {o.boletin_url && (
                        <div className="text-xs">
                          <a className="underline" href={o.boletin_url} target="_blank" rel="noreferrer">
                            Boletín oficial
                          </a>
                        </div>
                      )}
                    </td>
                    <td className="whitespace-nowrap pr-2">
                      {formatArs(o.monto)}
                      {o.is_duplicate_gasto && (
                        <div data-testid="republicacion" className="text-xs text-muted-foreground">
                          republicación
                        </div>
                      )}
                      {!o.en_ledger && (
                        <div className="text-xs text-muted-foreground">fuera del ledger</div>
                      )}
                    </td>
                    <td className="pr-2">
                      {o.ultima_clasificacion ? <ClasificacionChip value={o.ultima_clasificacion} /> : "-"}
                    </td>
                    <td>
                      {/* Sin `ejecucion_id` el acto no está en el ledger y la fase 2 todavía no
                          puede analizarlo: se dice, en vez de ofrecer un botón que no hace nada. */}
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!o.ejecucion_id || analizar.isPending}
                        title={
                          o.ejecucion_id
                            ? undefined
                            : "Este acto no está en el ledger de ejecución: el análisis de precio todavía no está disponible para él."
                        }
                        onClick={() => o.ejecucion_id && onAnalizar(o.ejecucion_id)}
                      >
                        Analizar en profundidad
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
