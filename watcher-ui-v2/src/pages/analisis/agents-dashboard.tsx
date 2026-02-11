import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function AgentsDashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard de Agentes</h1>
        <p className="text-muted-foreground mt-2">
          Monitoreo del sistema agéntico
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Agentes IA</CardTitle>
          <CardDescription>
            Estado y métricas de los agentes del sistema
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Funcionalidad en desarrollo - UI-3.1
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
