import { useMemo, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { MapaJurisdicciones } from "@/components/features/mapa-gasto"
import { useGastoPorJurisdiccion } from "@/lib/api"
import {
  COLOR_SIN_COBERTURA,
  METRICA_LABEL,
  TAMANO_LABEL,
  construirClases,
  etiquetaClase,
  jurisdiccionesVisibles,
  urlListado,
  valorMetrica,
} from "@/lib/mapa-gasto"
import { formatArs } from "@/lib/precio-mercado-format"
import type { JurisdiccionGasto, MetricaMapa, TamanoJurisdiccion } from "@/types/mapa-gasto"

const SELECT_CLASS = "mt-1 w-full rounded border border-border bg-background px-2 py-1 text-sm"
const METRICAS: MetricaMapa[] = ["gasto", "per_capita", "actos"]
const TAMANOS: TamanoJurisdiccion[] = ["todos", "grande", "mediano", "chico", "sin_poblacion"]

/** Leyenda con histograma: cada clase dice su rango, cuántas áreas caen y cuánto pesa. */
function LeyendaMetrica({
  metrica,
  clases,
  sinDatos,
}: {
  metrica: MetricaMapa
  clases: ReturnType<typeof construirClases>
  sinDatos: number
}) {
  const maximo = Math.max(1, sinDatos, ...clases.map((c) => c.count))
  return (
    <div data-testid="leyenda" className="rounded-md border border-border bg-muted/30 p-3 text-sm">
      <h3 className="font-medium">{METRICA_LABEL[metrica]}</h3>
      <p className="mb-2 text-xs text-muted-foreground">
        Escala por cuantiles entre las jurisdicciones con datos. La barra es la cantidad de áreas en cada rango.
      </p>
      <ul className="space-y-1">
        {clases.map((clase, i) => (
          <li key={i} data-testid="clase" className="flex items-center gap-2">
            <span
              aria-hidden="true"
              className="h-3 w-4 shrink-0 rounded-sm border border-black/20"
              style={{ backgroundColor: clase.color }}
            />
            <span className="w-40 shrink-0 tabular-nums">{etiquetaClase(clase, metrica)}</span>
            <span
              aria-hidden="true"
              className="h-2 rounded-sm"
              style={{ backgroundColor: clase.color, width: `${(clase.count / maximo) * 100}px` }}
            />
            <span data-testid="clase-count" className="text-xs text-muted-foreground">
              {clase.count} {clase.count === 1 ? "área" : "áreas"}
            </span>
          </li>
        ))}
        <li data-testid="clase-sin-datos" className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="h-3 w-4 shrink-0 rounded-sm border border-black/20"
            style={{ backgroundColor: COLOR_SIN_COBERTURA }}
          />
          <span className="w-40 shrink-0">Sin datos</span>
          <span
            aria-hidden="true"
            className="h-2 rounded-sm"
            style={{ backgroundColor: COLOR_SIN_COBERTURA, width: `${(sinDatos / maximo) * 100}px` }}
          />
          <span className="text-xs text-muted-foreground">{sinDatos} áreas</span>
        </li>
      </ul>
    </div>
  )
}

function ResumenGasto({ jurisdicciones }: { jurisdicciones: JurisdiccionGasto[] }) {
  const conCobertura = jurisdicciones.filter((j) => j.cobertura)
  const gasto = conCobertura.reduce((total, j) => total + j.gasto, 0)
  const actos = conCobertura.reduce((total, j) => total + j.actos, 0)
  return (
    <p data-testid="filtro-count" className="text-sm text-muted-foreground">
      {conCobertura.length} de {jurisdicciones.length} jurisdicciones con datos ·{" "}
      {actos} actos · {formatArs(gasto)} detectados en el filtro actual
    </p>
  )
}

function TablaDatos({ jurisdicciones, metrica }: { jurisdicciones: JurisdiccionGasto[]; metrica: MetricaMapa }) {
  const ordenadas = [...jurisdicciones].sort((a, b) => valorMetrica(b, metrica) - valorMetrica(a, metrica))
  return (
    <details data-testid="tabla-datos" className="rounded-md border border-border">
      <summary className="cursor-pointer p-3 text-sm font-medium">
        Ver los datos del mapa ({jurisdicciones.length} jurisdicciones)
      </summary>
      <div className="max-h-80 overflow-auto">
        <table className="w-full text-left text-xs">
          <thead className="sticky top-0 bg-background text-muted-foreground">
            <tr>
              <th className="p-2">Jurisdicción</th>
              <th>Tipo</th>
              <th>Departamento</th>
              <th className="text-right">Población 2022</th>
              <th className="text-right">Gasto detectado</th>
              <th className="text-right">Per cápita</th>
              <th className="text-right">Actos</th>
            </tr>
          </thead>
          <tbody>
            {ordenadas.map((j) => (
              <tr key={j.codigo} className="border-t border-border">
                <td className="p-2">
                  <a className="underline" href={urlListado(j)}>
                    {j.nombre}
                  </a>
                </td>
                <td>{j.tipo}</td>
                <td>{j.departamento ?? "-"}</td>
                <td className="text-right tabular-nums">{j.poblacion_2022 ?? "-"}</td>
                <td className="text-right tabular-nums">{j.cobertura ? formatArs(j.gasto) : "sin datos"}</td>
                <td className="text-right tabular-nums">{formatArs(j.gasto_per_capita)}</td>
                <td className="text-right tabular-nums">{j.cobertura ? j.actos : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

export function MapaGastoPage() {
  const { data, isLoading, isError } = useGastoPorJurisdiccion()
  const [metrica, setMetrica] = useState<MetricaMapa>("gasto")
  const [tamano, setTamano] = useState<TamanoJurisdiccion>("todos")

  const jurisdicciones = useMemo(() => data?.jurisdicciones ?? [], [data])
  const clases = useMemo(() => construirClases(jurisdicciones, metrica), [jurisdicciones, metrica])
  const visibles = useMemo(
    () => jurisdiccionesVisibles(jurisdicciones, tamano),
    [jurisdicciones, tamano],
  )
  const sinDatos = visibles.filter((j) => !j.cobertura).length
  const provincial = data?.por_nivel.find((n) => n.nivel === "provincial")

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Mapa de gasto por jurisdicción</h1>
        <p className="mt-2 text-muted-foreground">
          Gasto público detectado en los boletines y portales del corte, por municipio y comuna de
          Córdoba. El gris no es gasto cero: es una jurisdicción sin datos en el corte.
        </p>
      </div>

      {isLoading && <p className="text-sm text-muted-foreground">Cargando el gasto por jurisdicción...</p>}
      {isError && <p className="text-sm text-red-400">No se pudo cargar el gasto por jurisdicción.</p>}

      {data && (
        <>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4" data-testid="resumen">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Municipios y comunas</CardDescription>
                <CardTitle className="text-2xl">{formatArs(data.totales.gasto)}</CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                {data.totales.actos} actos · {data.totales.con_cobertura} de {data.totales.jurisdicciones} jurisdicciones con datos
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Gasto provincial</CardDescription>
                <CardTitle className="text-2xl">{formatArs(provincial?.gasto ?? null)}</CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                No se reparte entre municipios: no hay forma de saber en qué jurisdicción se gastó.
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Sin municipio asignado</CardDescription>
                <CardTitle className="text-2xl">{formatArs(data.sin_jurisdiccion.gasto)}</CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                {data.sin_jurisdiccion.actos} actos municipales o comunales que no nombran su gobierno local.
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Cobertura</CardDescription>
                <CardTitle className="text-2xl">
                  {data.totales.con_cobertura} / {data.totales.jurisdicciones}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                Jurisdicciones con al menos un acto de gasto en el corte.
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            <label className="text-sm">
              <span className="text-muted-foreground">Métrica</span>
              <select
                data-testid="metrica-select"
                className={SELECT_CLASS}
                value={metrica}
                onChange={(e) => setMetrica(e.target.value as MetricaMapa)}
              >
                {METRICAS.map((m) => (
                  <option key={m} value={m}>{METRICA_LABEL[m]}</option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="text-muted-foreground">Tamaño del municipio</span>
              <select
                data-testid="tamano-select"
                className={SELECT_CLASS}
                value={tamano}
                onChange={(e) => setTamano(e.target.value as TamanoJurisdiccion)}
              >
                {TAMANOS.map((t) => (
                  <option key={t} value={t}>{TAMANO_LABEL[t]}</option>
                ))}
              </select>
            </label>
          </div>

          <ResumenGasto jurisdicciones={visibles} />

          <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
            <MapaJurisdicciones
              jurisdicciones={jurisdicciones}
              clases={clases}
              metrica={metrica}
              tamano={tamano}
            />
            <div className="space-y-3">
              <LeyendaMetrica metrica={metrica} clases={clases} sinDatos={sinDatos} />
              <div className="rounded-md border border-border bg-muted/30 p-3 text-xs text-muted-foreground">
                <p>
                  <span className="text-foreground">Sin dictamen.</span> El mapa muestra los montos
                  detectados y su fuente; no clasifica ni califica el gasto.
                </p>
                <p className="mt-1">
                  En muchos actos el monto es el presupuesto oficial del llamado, no lo adjudicado ni
                  lo pagado.
                </p>
              </div>
            </div>
          </div>

          <TablaDatos jurisdicciones={visibles} metrica={metrica} />

          <p data-testid="fuente-mapa" className="text-xs text-muted-foreground">
            Nombres y población: {data.fuente.catalogo}; {data.fuente.poblacion}. Límites:{" "}
            {data.fuente.limites}. Extraídos el {data.fuente.fecha}. {data.fuente.nota}
          </p>
        </>
      )}
    </div>
  )
}
