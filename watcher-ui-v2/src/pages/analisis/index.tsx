import { useNavigate } from "@tanstack/react-router"
import { Bot, AlertTriangle, Workflow } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function AnalisisHub() {
  const navigate = useNavigate()

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Análisis</h1>
        <p className="text-muted-foreground mt-2">
          Análisis presupuestario y detección de anomalías
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
              Abrir Dashboard →
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
              Gestión de alertas y anomalías
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Revisa y gestiona alertas detectadas por el sistema
            </p>
            <Button variant="outline" size="sm" className="w-full">
              Ver Alertas →
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
              Gestión de flujos de trabajo
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">
              Próximamente disponible
            </p>
            <Button variant="outline" size="sm" className="w-full" disabled>
              Próximamente
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
