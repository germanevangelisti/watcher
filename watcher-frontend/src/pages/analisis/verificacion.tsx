import { Shield, AlertTriangle, CheckCircle2, HelpCircle, XCircle } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useVCPMetrics } from "@/lib/api/hooks"

export function VerificacionPage() {
  const { data: metrics, isLoading, error } = useVCPMetrics({ refetchInterval: 30_000 })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Cargando métricas de verificación...</div>
      </div>
    )
  }

  if (error || !metrics) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Error al cargar métricas adversariales</div>
      </div>
    )
  }

  const vcpPct = Math.round(metrics.vcp_score * 100)
  const scoreColor =
    metrics.vcp_score >= 0.85 ? "text-green-400" :
    metrics.vcp_score >= 0.70 ? "text-yellow-400" : "text-red-400"

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Shield className="h-7 w-7 text-indigo-400" />
        <div>
          <h1 className="text-2xl font-bold">Verificación Adversarial</h1>
          <p className="text-sm text-muted-foreground">
            Sistema VCP — Verified Claim Precision
          </p>
        </div>
        {metrics.requires_attention && (
          <Badge variant="destructive" className="ml-auto flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            Requiere atención
          </Badge>
        )}
      </div>

      {/* VCP Score */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="md:col-span-1">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              VCP Score Global
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-5xl font-bold ${scoreColor}`}>{vcpPct}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              {metrics.sample_count} análisis procesados
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <CheckCircle2 className="h-4 w-4 text-green-400" /> Verificadas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-400">{metrics.verified}</div>
            <p className="text-xs text-muted-foreground">de {metrics.total_aius} AIUs</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <HelpCircle className="h-4 w-4 text-yellow-400" /> No verificables
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-yellow-400">{metrics.unverifiable}</div>
            <p className="text-xs text-muted-foreground">de {metrics.total_aius} AIUs</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
              <XCircle className="h-4 w-4 text-red-400" /> Contradichas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-400">{metrics.contradicted}</div>
            <p className="text-xs text-muted-foreground">de {metrics.total_aius} AIUs</p>
          </CardContent>
        </Card>
      </div>

      {/* Latency info */}
      {(metrics.latency_p50_ms != null || metrics.latency_p95_ms != null) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Latencia de verificación</CardTitle>
          </CardHeader>
          <CardContent className="flex gap-8">
            {metrics.latency_p50_ms != null && (
              <div>
                <div className="text-2xl font-bold">{Math.round(metrics.latency_p50_ms)} ms</div>
                <div className="text-xs text-muted-foreground">p50</div>
              </div>
            )}
            {metrics.latency_p95_ms != null && (
              <div>
                <div className="text-2xl font-bold">{Math.round(metrics.latency_p95_ms)} ms</div>
                <div className="text-xs text-muted-foreground">p95</div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
