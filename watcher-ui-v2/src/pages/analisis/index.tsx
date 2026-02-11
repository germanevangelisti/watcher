import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function AnalisisHub() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Análisis</h1>
        <p className="text-muted-foreground mt-2">
          Análisis presupuestario y detección de anomalías
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Panel de Análisis</CardTitle>
          <CardDescription>
            Herramientas de análisis y visualización de datos
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Funcionalidad en desarrollo - Futuras épicas
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
