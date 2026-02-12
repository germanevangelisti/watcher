import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import dayjs from "dayjs"
import { AlertTriangle, CheckCircle2, XCircle, Filter } from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { FadeTransition } from "@/components/ui/fade-transition"
import { useAlertas, useAlertasStats } from "@/lib/api/hooks"

export default function AlertasPage() {
  const navigate = useNavigate()
  const [filters, setFilters] = useState({
    nivel_severidad: undefined as string | undefined,
    estado: undefined as string | undefined,
    search: "",
  })

  const alertasQuery = useAlertas({
    nivel_severidad: filters.nivel_severidad,
    estado: filters.estado,
    limit: 50,
  })

  const statsQuery = useAlertasStats()

  const filteredAlertas = alertasQuery.data?.alertas.filter((alerta) => {
    if (!filters.search) return true
    const searchLower = filters.search.toLowerCase()
    return (
      alerta.titulo.toLowerCase().includes(searchLower) ||
      alerta.organismo.toLowerCase().includes(searchLower) ||
      alerta.tipo_alerta.toLowerCase().includes(searchLower)
    )
  })

  const getSeverityColor = (nivel: string) => {
    switch (nivel) {
      case "critica": return "bg-red-500/10 text-red-400 border-red-500/20"
      case "alta": return "bg-orange-500/10 text-orange-400 border-orange-500/20"
      case "media": return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
      case "baja": return "bg-blue-500/10 text-blue-400 border-blue-500/20"
      default: return "bg-gray-500/10 text-gray-400 border-gray-500/20"
    }
  }

  const getEstadoIcon = (estado: string) => {
    switch (estado) {
      case "activa": return <AlertTriangle className="h-4 w-4 text-orange-400" />
      case "revisada": return <CheckCircle2 className="h-4 w-4 text-green-400" />
      case "descartada": return <XCircle className="h-4 w-4 text-gray-400" />
      default: return null
    }
  }

  const getEstadoColor = (estado: string) => {
    switch (estado) {
      case "activa": return "bg-orange-500/10 text-orange-400 border-orange-500/20"
      case "revisada": return "bg-green-500/10 text-green-400 border-green-500/20"
      case "descartada": return "bg-gray-500/10 text-gray-400 border-gray-500/20"
      default: return "bg-gray-500/10 text-gray-400 border-gray-500/20"
    }
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Alertas</h1>
        <p className="text-muted-foreground mt-2">
          Monitoreo de alertas y anomalías detectadas
        </p>
      </div>

      {/* Stats Cards */}
      <FadeTransition
        isLoading={statsQuery.isLoading}
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
        {statsQuery.data && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total</p>
                    <p className="text-2xl font-bold">{statsQuery.data.total}</p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-blue-400" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Críticas</p>
                    <p className="text-2xl font-bold text-red-400">{statsQuery.data.criticas}</p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-red-400" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Activas</p>
                    <p className="text-2xl font-bold text-orange-400">{statsQuery.data.activas}</p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-orange-400" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Revisadas</p>
                    <p className="text-2xl font-bold text-green-400">{statsQuery.data.revisadas}</p>
                  </div>
                  <CheckCircle2 className="h-8 w-8 text-green-400" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </FadeTransition>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filtros
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Input
              placeholder="Buscar por título, organismo o tipo..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            />

            <Select
              value={filters.nivel_severidad || "all"}
              onValueChange={(value) => 
                setFilters({ ...filters, nivel_severidad: value === "all" ? undefined : value })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Severidad" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas las severidades</SelectItem>
                <SelectItem value="critica">Crítica</SelectItem>
                <SelectItem value="alta">Alta</SelectItem>
                <SelectItem value="media">Media</SelectItem>
                <SelectItem value="baja">Baja</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={filters.estado || "all"}
              onValueChange={(value) => 
                setFilters({ ...filters, estado: value === "all" ? undefined : value })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los estados</SelectItem>
                <SelectItem value="activa">Activas</SelectItem>
                <SelectItem value="revisada">Revisadas</SelectItem>
                <SelectItem value="descartada">Descartadas</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Alertas List */}
      <FadeTransition
        isLoading={alertasQuery.isLoading}
        skeleton={
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <Skeleton className="h-24 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        }
      >
        <div className="space-y-4">
          {alertasQuery.isError && (
            <Card className="border-red-500/20">
              <CardContent className="p-6 text-center text-red-400">
                Error cargando alertas: {(alertasQuery.error as Error).message}
              </CardContent>
            </Card>
          )}

          {filteredAlertas && filteredAlertas.length === 0 && (
            <Card>
              <CardContent className="p-12 text-center">
                <AlertTriangle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">No se encontraron alertas</p>
              </CardContent>
            </Card>
          )}

          {filteredAlertas?.map((alerta) => (
            <Card
              key={alerta.id}
              className="hover:bg-surface-elevated transition-colors cursor-pointer"
              onClick={() => navigate({ to: `/analisis/alertas/${alerta.id}` })}
            >
              <CardContent className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 space-y-3">
                    {/* Header */}
                    <div className="flex items-start gap-3">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold">{alerta.titulo}</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          {alerta.organismo}
                          {alerta.programa && ` - ${alerta.programa}`}
                        </p>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Badge className={getSeverityColor(alerta.nivel_severidad)}>
                          {alerta.nivel_severidad.toUpperCase()}
                        </Badge>
                        <Badge className={getEstadoColor(alerta.estado)}>
                          <span className="flex items-center gap-1">
                            {getEstadoIcon(alerta.estado)}
                            {alerta.estado}
                          </span>
                        </Badge>
                      </div>
                    </div>

                    {/* Description */}
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {alerta.descripcion}
                    </p>

                    {/* Metrics */}
                    {(alerta.valor_detectado != null || alerta.porcentaje_desvio != null) && (
                      <div className="flex items-center gap-6 text-sm">
                        {alerta.valor_detectado != null && (
                          <div>
                            <span className="text-muted-foreground">Detectado: </span>
                            <span className="font-mono text-orange-400">
                              ${alerta.valor_detectado.toLocaleString()}
                            </span>
                          </div>
                        )}
                        {alerta.valor_esperado != null && (
                          <div>
                            <span className="text-muted-foreground">Esperado: </span>
                            <span className="font-mono">
                              ${alerta.valor_esperado.toLocaleString()}
                            </span>
                          </div>
                        )}
                        {alerta.porcentaje_desvio != null && (
                          <div>
                            <span className="text-muted-foreground">Desvío: </span>
                            <span className={`font-mono ${
                              Math.abs(alerta.porcentaje_desvio) > 20 ? "text-red-400" : "text-yellow-400"
                            }`}>
                              {alerta.porcentaje_desvio > 0 ? "+" : ""}
                              {alerta.porcentaje_desvio.toFixed(1)}%
                            </span>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Footer */}
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <div className="flex items-center gap-4">
                        <span>{alerta.tipo_alerta}</span>
                        <span>•</span>
                        <span>Detectada {dayjs(alerta.fecha_deteccion).format("DD/MM/YYYY HH:mm")}</span>
                      </div>
                      <Button variant="ghost" size="sm">
                        Ver detalles →
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </FadeTransition>
    </div>
  )
}
