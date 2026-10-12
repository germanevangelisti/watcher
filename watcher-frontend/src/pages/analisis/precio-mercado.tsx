import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAnalizarPrecio, useObservables } from "@/lib/api"
import type { AnalisisPrecio, Clasificacion } from "@/types/precio-mercado"
import { CLASIFICACION_LABEL, formatArs } from "@/lib/precio-mercado-format"

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

export function PrecioMercadoPage() {
  const [q, setQ] = useState("")
  const [selected, setSelected] = useState<number | null>(null)
  const { data, isLoading, isError } = useObservables({ q })
  const analizar = useAnalizarPrecio()

  const onAnalizar = (id: number) => {
    setSelected(id)
    analizar.mutate(id)
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Precio de mercado</h1>
        <p className="mt-2 text-muted-foreground">
          Compras de bienes estandarizables detectadas en los boletines. El análisis se corre a pedido,
          compara el precio unitario contra referencias con fuente y fecha, y no emite dictamen.
        </p>
      </div>

      <Input
        placeholder="Filtrar por concepto u organismo..."
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className="max-w-md"
      />

      {analizar.isPending && <p className="text-sm text-muted-foreground">Analizando el acto {selected}... puede tardar con el modelo local.</p>}
      {analizar.isError && <p className="text-sm text-red-400">No se pudo completar el análisis.</p>}
      {analizar.data && <Resultado data={analizar.data} />}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Gastos observables</CardTitle>
          <CardDescription>{data ? `${data.total} actos detectados` : " "}</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading && <p className="text-sm text-muted-foreground">Cargando...</p>}
          {isError && <p className="text-sm text-red-400">No se pudo cargar la lista.</p>}
          {data && data.items.length === 0 && <p className="text-sm text-muted-foreground">Sin actos para este filtro.</p>}
          {data && data.items.length > 0 && (
            <table className="w-full text-left text-sm" data-testid="observables">
              <thead className="text-muted-foreground">
                <tr><th>Fecha</th><th>Organismo</th><th>Concepto</th><th>Monto</th><th>Último análisis</th><th></th></tr>
              </thead>
              <tbody>
                {data.items.map((o) => (
                  <tr key={o.id} className="border-t border-border align-top">
                    <td className="whitespace-nowrap pr-2">{o.fecha}</td>
                    <td className="pr-2">{o.organismo}</td>
                    <td className="pr-2">{o.concepto}<div className="text-xs text-muted-foreground">{o.motivo}</div></td>
                    <td className="whitespace-nowrap pr-2">{formatArs(o.monto)}</td>
                    <td className="pr-2">{o.ultima_clasificacion ? <ClasificacionChip value={o.ultima_clasificacion} /> : "-"}</td>
                    <td>
                      <Button size="sm" variant="outline" disabled={analizar.isPending} onClick={() => onAnalizar(o.id)}>
                        Analizar
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
