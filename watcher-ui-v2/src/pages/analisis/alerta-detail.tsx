import { useState } from "react"
import { useParams, useNavigate } from "@tanstack/react-router"
import dayjs from "dayjs"
import { 
  ArrowLeft, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle,
  Calendar,
  Building2,
  FileText,
  TrendingUp
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { FadeTransition } from "@/components/ui/fade-transition"
import { useAlerta, useUpdateAlerta } from "@/lib/api/hooks"

export default function AlertaDetailPage() {
  const { alertaId } = useParams({ from: "/analisis/alertas/$alertaId" })
  const navigate = useNavigate()
  const alertaQuery = useAlerta(Number(alertaId))
  const updateMutation = useUpdateAlerta()

  const [nuevoEstado, setNuevoEstado] = useState<string>("")
  const [observaciones, setObservaciones] = useState("")

  const handleUpdateEstado = async () => {
    if (!nuevoEstado || !alertaQuery.data) return

    try {
      await updateMutation.mutateAsync({
        alertaId: alertaQuery.data.id,
        update: {
          estado: nuevoEstado as "activa" | "revisada" | "descartada",
          observaciones_revision: observaciones || undefined,
        },
      })
      setNuevoEstado("")
      setObservaciones("")
    } catch (error) {
      console.error("Error updating alerta:", error)
    }
  }

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
      case "activa": return <AlertTriangle className="h-5 w-5 text-orange-400" />
      case "revisada": return <CheckCircle2 className="h-5 w-5 text-green-400" />
      case "descartada": return <XCircle className="h-5 w-5 text-gray-400" />
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
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate({ to: "/analisis/alertas" })}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Volver
        </Button>
      </div>

      <FadeTransition
        isLoading={alertaQuery.isLoading}
        skeleton={
          <div className="space-y-6">
            <Card>
              <CardContent className="p-6">
                <Skeleton className="h-32 w-full" />
              </CardContent>
            </Card>
          </div>
        }
      >
        {alertaQuery.isError && (
          <Card className="border-red-500/20">
            <CardContent className="p-6 text-center text-red-400">
              Error cargando alerta: {(alertaQuery.error as Error).message}
            </CardContent>
          </Card>
        )}

        {alertaQuery.data && (
          <div className="space-y-6">
            {/* Main Info Card */}
            <Card>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <CardTitle className="text-2xl">{alertaQuery.data.titulo}</CardTitle>
                    <div className="flex items-center gap-2">
                      <Badge className={getSeverityColor(alertaQuery.data.nivel_severidad)}>
                        {alertaQuery.data.nivel_severidad.toUpperCase()}
                      </Badge>
                      <Badge className={getEstadoColor(alertaQuery.data.estado)}>
                        <span className="flex items-center gap-1">
                          {getEstadoIcon(alertaQuery.data.estado)}
                          {alertaQuery.data.estado}
                        </span>
                      </Badge>
                      <Badge variant="outline">{alertaQuery.data.tipo_alerta}</Badge>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex items-start gap-3">
                    <Building2 className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <p className="text-sm text-muted-foreground">Organismo</p>
                      <p className="font-medium">{alertaQuery.data.organismo}</p>
                      {alertaQuery.data.programa && (
                        <p className="text-sm text-muted-foreground mt-1">
                          Programa: {alertaQuery.data.programa}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div>
                      <p className="text-sm text-muted-foreground">Fecha de detección</p>
                      <p className="font-medium">
                        {dayjs(alertaQuery.data.fecha_deteccion).format("DD/MM/YYYY HH:mm")}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3 pt-4 border-t">
                  <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm text-muted-foreground mb-2">Descripción</p>
                    <p className="text-sm leading-relaxed">{alertaQuery.data.descripcion}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Metrics Card */}
            {(alertaQuery.data.valor_detectado != null || 
              alertaQuery.data.valor_esperado != null || 
              alertaQuery.data.porcentaje_desvio != null) && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5" />
                    Métricas
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {alertaQuery.data.valor_detectado != null && (
                      <div>
                        <p className="text-sm text-muted-foreground mb-1">Valor Detectado</p>
                        <p className="text-2xl font-bold font-mono text-orange-400">
                          ${alertaQuery.data.valor_detectado.toLocaleString()}
                        </p>
                      </div>
                    )}

                    {alertaQuery.data.valor_esperado != null && (
                      <div>
                        <p className="text-sm text-muted-foreground mb-1">Valor Esperado</p>
                        <p className="text-2xl font-bold font-mono">
                          ${alertaQuery.data.valor_esperado.toLocaleString()}
                        </p>
                      </div>
                    )}

                    {alertaQuery.data.porcentaje_desvio != null && (
                      <div>
                        <p className="text-sm text-muted-foreground mb-1">Desvío</p>
                        <p className={`text-2xl font-bold font-mono ${
                          Math.abs(alertaQuery.data.porcentaje_desvio) > 20 ? "text-red-400" : "text-yellow-400"
                        }`}>
                          {alertaQuery.data.porcentaje_desvio > 0 ? "+" : ""}
                          {alertaQuery.data.porcentaje_desvio.toFixed(1)}%
                        </p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Acciones Sugeridas */}
            {alertaQuery.data.acciones_sugeridas && (
              <Card>
                <CardHeader>
                  <CardTitle>Acciones Sugeridas</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="text-sm bg-surface-elevated p-4 rounded-md overflow-auto">
                    {JSON.stringify(alertaQuery.data.acciones_sugeridas, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}

            {/* Update Estado */}
            <Card>
              <CardHeader>
                <CardTitle>Actualizar Estado</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium mb-2 block">Nuevo Estado</label>
                    <Select value={nuevoEstado} onValueChange={setNuevoEstado}>
                      <SelectTrigger>
                        <SelectValue placeholder="Seleccionar estado..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="activa">Activa</SelectItem>
                        <SelectItem value="revisada">Revisada</SelectItem>
                        <SelectItem value="descartada">Descartada</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Observaciones (opcional)
                  </label>
                  <textarea
                    className="w-full min-h-[100px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    placeholder="Agregar observaciones sobre la revisión..."
                    value={observaciones}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setObservaciones(e.target.value)}
                    rows={4}
                  />
                </div>

                <Button
                  onClick={handleUpdateEstado}
                  disabled={!nuevoEstado || updateMutation.isPending}
                  className="w-full md:w-auto"
                >
                  {updateMutation.isPending ? "Actualizando..." : "Actualizar Estado"}
                </Button>
              </CardContent>
            </Card>
          </div>
        )}
      </FadeTransition>
    </div>
  )
}
