import { useNavigate } from "@tanstack/react-router"
import { Bot, AlertTriangle, Workflow, Activity } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function AnalisisHub() {
  const navigate = useNavigate()

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analisis</h1>
        <p className="text-muted-foreground mt-2">
          Analisis presupuestario y deteccion de anomalias
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Pipeline Status */}
        <Card className="hover:bg-surface-elevated transition-colors cursor-pointer"
              onClick={() => navigate({ to: "/analisis/pipeline" })}>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/10">
                <Activity className="h-6 w-6 text-green-400" />
              </div>
              <CardTitle>Pipeline</CardTitle>
            </div>
            <CardDescription>
              Estado del pipeline de procesamiento
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Metricas, errores y actividad del pipeline en tiempo real
            </p>
            <Button variant="outline" size="sm" className="w-full">
              Ver Pipeline &rarr;
            </Button>
          </CardContent>
        </Card>

        {/* Agents Dashboard */}
        <Card className="hover:bg-surface-elevated transition-colors cursor-pointer"
              onClick={() => navigate({ to: "/analisis/agentes" })}>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <Bot className="h-6 w-6 text-blue-400" />
              </div>
              <CardTitle>Agentes IA</CardTitle>
            </div>
            <CardDescription>
              Panel de control de agentes inteligentes
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Monitorea el estado de los agentes y consulta insights del sistema
            </p>
            <Button variant="outline" size="sm" className="w-full">
              Abrir Dashboard &rarr;
            </Button>
          </CardContent>
        </Card>

        {/* Alertas */}
        <Card className="hover:bg-surface-elevated transition-colors cursor-pointer"
              onClick={() => navigate({ to: "/analisis/alertas" })}>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-orange-500/10">
                <AlertTriangle className="h-6 w-6 text-orange-400" />
              </div>
              <CardTitle>Alertas</CardTitle>
            </div>
            <CardDescription>
              Gestion de alertas y anomalias
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Revisa y gestiona alertas detectadas por el sistema
            </p>
            <Button variant="outline" size="sm" className="w-full">
              Ver Alertas &rarr;
            </Button>
          </CardContent>
        </Card>

        {/* Workflows (placeholder) */}
        <Card className="opacity-50">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/10">
                <Workflow className="h-6 w-6 text-purple-400" />
              </div>
              <CardTitle>Workflows</CardTitle>
            </div>
            <CardDescription>
              Gestion de flujos de trabajo
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Proximamente disponible
            </p>
            <Button variant="outline" size="sm" className="w-full" disabled>
              Proximamente
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
