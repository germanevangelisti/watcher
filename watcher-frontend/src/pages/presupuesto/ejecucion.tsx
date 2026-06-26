import { useState } from "react"
import dayjs from "dayjs"
import {
  BarChart3,
  Filter,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Copy,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Skeleton } from "@/components/ui/skeleton"
import { FadeTransition } from "@/components/ui/fade-transition"
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "@/components/ui/table"
import { useEjecucion, useEjecucionResumen } from "@/lib/api/hooks"

const PAGE_SIZE = 50

function formatARS(value: number | null | undefined): string {
  if (value == null) return "—"
  if (value >= 1e9) return `$${(value / 1e9).toFixed(1)}B`
  if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`
  return `$${value.toLocaleString("es-AR")}`
}

function RiesgoBadge({ riesgo }: { riesgo?: string }) {
  if (!riesgo) return <span className="text-muted-foreground text-xs">—</span>
  const colorMap: Record<string, string> = {
    alto: "bg-red-500/10 text-red-400 border-red-500/20",
    medio: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    bajo: "bg-green-500/10 text-green-400 border-green-500/20",
  }
  const color = colorMap[riesgo.toLowerCase()] ?? "bg-gray-500/10 text-gray-400 border-gray-500/20"
  return <Badge className={color}>{riesgo}</Badge>
}

export function EjecucionPresupuestariaPage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({
    organismo: "",
    riesgo: undefined as string | undefined,
    solo_canonicos: true,
    requiere_revision: undefined as boolean | undefined,
  })

  const resumenQuery = useEjecucionResumen()

  const ejecucionQuery = useEjecucion({
    skip: (page - 1) * PAGE_SIZE,
    limit: PAGE_SIZE,
    organismo: filters.organismo || undefined,
    riesgo: filters.riesgo,
    solo_canonicos: filters.solo_canonicos,
    requiere_revision: filters.requiere_revision,
  })

  const totalPages = ejecucionQuery.data?.total
    ? Math.ceil(ejecucionQuery.data.total / PAGE_SIZE)
    : 0

  function handleFilterChange(patch: Partial<typeof filters>) {
    setFilters((f) => ({ ...f, ...patch }))
    setPage(1)
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Ejecución Presupuestaria 2026</h1>
        <p className="text-muted-foreground mt-2">
          Actos publicados en el Boletín Oficial con deduplicación automática
        </p>
      </div>

      {/* Summary Cards */}
      <FadeTransition
        isLoading={resumenQuery.isLoading}
        skeleton={
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <Skeleton className="h-12 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        }
      >
        {resumenQuery.data && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Actos canónicos</p>
                    <p className="text-2xl font-bold">
                      {(resumenQuery.data.total_canonical ?? 0).toLocaleString()}
                    </p>
                  </div>
                  <CheckCircle2 className="h-8 w-8 text-green-400" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Monto total</p>
                    <p className="text-2xl font-bold text-blue-400">
                      {formatARS(resumenQuery.data.monto_canonical)}
                    </p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-blue-400" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Duplicados detectados</p>
                    <p className="text-2xl font-bold text-orange-400">
                      {(resumenQuery.data.total_duplicates ?? 0).toLocaleString()}
                    </p>
                  </div>
                  <Copy className="h-8 w-8 text-orange-400" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Monto duplicado</p>
                    <p className="text-2xl font-bold text-muted-foreground">
                      {formatARS(resumenQuery.data.monto_duplicates)}
                    </p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </FadeTransition>

      {/* Monthly breakdown */}
      {resumenQuery.data?.por_mes && resumenQuery.data.por_mes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 className="h-4 w-4" />
              Evolución mensual (canónicos)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {resumenQuery.data.por_mes.map((item) => {
                const maxMonto = Math.max(
                  ...resumenQuery.data!.por_mes.map((m) => m.monto_total)
                )
                const pct = maxMonto > 0 ? (item.monto_total / maxMonto) * 100 : 0
                return (
                  <div key={item.mes} className="flex items-center gap-3">
                    <span className="text-sm text-muted-foreground w-16 shrink-0">
                      {dayjs(item.mes + "-01").format("MMM YY")}
                    </span>
                    <div className="flex-1 bg-muted rounded h-4 overflow-hidden">
                      <div
                        className="h-full bg-blue-500/70 rounded"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-sm font-mono w-20 text-right shrink-0">
                      {formatARS(item.monto_total)}
                    </span>
                    <span className="text-xs text-muted-foreground w-16 text-right shrink-0">
                      {item.count} actos
                    </span>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Top organisms */}
      {resumenQuery.data?.por_organismo && resumenQuery.data.por_organismo.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top organismos por monto</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {resumenQuery.data.por_organismo.slice(0, 10).map((item, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground truncate flex-1 pr-4">
                    {item.organismo ?? "(sin organismo)"}
                  </span>
                  <div className="flex items-center gap-4 shrink-0">
                    <span className="text-xs text-muted-foreground">{item.count} actos</span>
                    <span className="font-mono font-medium">{formatARS(item.monto_total)}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filtros
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <Input
              placeholder="Buscar organismo..."
              value={filters.organismo}
              onChange={(e) => handleFilterChange({ organismo: e.target.value })}
            />

            <Select
              value={filters.riesgo ?? "all"}
              onValueChange={(v) =>
                handleFilterChange({ riesgo: v === "all" ? undefined : v })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Nivel de riesgo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los riesgos</SelectItem>
                <SelectItem value="alto">Alto</SelectItem>
                <SelectItem value="medio">Medio</SelectItem>
                <SelectItem value="bajo">Bajo</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={
                filters.requiere_revision === undefined
                  ? "all"
                  : filters.requiere_revision
                  ? "si"
                  : "no"
              }
              onValueChange={(v) =>
                handleFilterChange({
                  requiere_revision:
                    v === "all" ? undefined : v === "si",
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Revisión" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="si">Requiere revisión</SelectItem>
                <SelectItem value="no">Sin observaciones</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex items-center gap-3">
              <Switch
                id="solo-canonicos"
                checked={filters.solo_canonicos}
                onCheckedChange={(checked) =>
                  handleFilterChange({ solo_canonicos: checked })
                }
              />
              <Label htmlFor="solo-canonicos" className="text-sm cursor-pointer">
                Solo canónicos
              </Label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <FadeTransition
        isLoading={ejecucionQuery.isLoading}
        skeleton={
          <Card>
            <CardContent className="p-6 space-y-3">
              {[...Array(8)].map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </CardContent>
          </Card>
        }
      >
        <Card>
          <CardContent className="p-0">
            {ejecucionQuery.isError && (
              <div className="p-6 text-center text-red-400">
                Error cargando ejecuciones: {(ejecucionQuery.error as Error).message}
              </div>
            )}

            {ejecucionQuery.data && (
              <>
                <div className="flex items-center justify-between px-4 py-3 border-b">
                  <span className="text-sm text-muted-foreground">
                    {(ejecucionQuery.data.total ?? 0).toLocaleString()} actos
                    {" · "}
                    total {formatARS(ejecucionQuery.data.total_monto)}
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      {page} / {totalPages || 1}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-24">Fecha</TableHead>
                        <TableHead>Organismo</TableHead>
                        <TableHead>Beneficiario</TableHead>
                        <TableHead className="max-w-xs">Concepto</TableHead>
                        <TableHead className="text-right">Monto</TableHead>
                        <TableHead>Riesgo</TableHead>
                        <TableHead>Estado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {ejecucionQuery.data.ejecuciones.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={7} className="text-center text-muted-foreground py-12">
                            No se encontraron ejecuciones
                          </TableCell>
                        </TableRow>
                      )}
                      {ejecucionQuery.data.ejecuciones.map((ej) => (
                        <TableRow
                          key={ej.id}
                          className={ej.is_duplicate ? "opacity-50" : undefined}
                        >
                          <TableCell className="text-sm font-mono whitespace-nowrap">
                            {dayjs(ej.fecha_boletin).format("DD/MM/YY")}
                          </TableCell>
                          <TableCell className="text-sm max-w-[180px] truncate">
                            {ej.organismo ?? "—"}
                          </TableCell>
                          <TableCell className="text-sm max-w-[180px] truncate text-muted-foreground">
                            {ej.beneficiario ?? "—"}
                          </TableCell>
                          <TableCell className="text-sm max-w-xs truncate text-muted-foreground">
                            {ej.concepto ?? "—"}
                          </TableCell>
                          <TableCell className="text-right font-mono text-sm whitespace-nowrap">
                            {formatARS(ej.monto)}
                          </TableCell>
                          <TableCell>
                            <RiesgoBadge riesgo={ej.riesgo_watcher} />
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              {ej.is_duplicate ? (
                                <Badge className="bg-orange-500/10 text-orange-400 border-orange-500/20 text-xs">
                                  dup
                                </Badge>
                              ) : ej.requiere_revision ? (
                                <Badge className="bg-yellow-500/10 text-yellow-400 border-yellow-500/20 text-xs">
                                  revisar
                                </Badge>
                              ) : (
                                <Badge className="bg-green-500/10 text-green-400 border-green-500/20 text-xs">
                                  ok
                                </Badge>
                              )}
                              {ej.presupuesto_base_id && (
                                <Badge
                                  className="bg-blue-500/10 text-blue-400 border-blue-500/20 text-xs"
                                  title={`Programa: ${ej.programa ?? ""}`}
                                >
                                  pb
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </FadeTransition>
    </div>
  )
}
