import { useState } from "react"
import { AppShell } from "./components/layout/app-shell"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card"
import { Badge } from "./components/ui/badge"
import { Skeleton } from "./components/ui/skeleton"
import { useDashboardStats } from "./lib/api/hooks/use-dashboard-stats"

function App() {
  const [currentPath, setCurrentPath] = useState("/")
  const { data: stats, isLoading, error } = useDashboardStats()

  const getPageContent = () => {
    switch (currentPath) {
      case "/":
        return (
          <div className="space-y-6">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
              <p className="text-muted-foreground mt-2">
                Bienvenido a Watcher UI v2 - Sistema de análisis de documentos oficiales
              </p>
            </div>

            {error && (
              <Card className="border-danger">
                <CardHeader>
                  <CardTitle className="text-danger">Error de conexión</CardTitle>
                  <CardDescription>
                    No se pudo conectar con el backend. Asegúrate de que el servidor esté corriendo en http://localhost:8001
                  </CardDescription>
                </CardHeader>
              </Card>
            )}

            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader>
                  {isLoading ? (
                    <>
                      <Skeleton className="h-8 w-32" />
                      <Skeleton className="h-4 w-48 mt-2" />
                    </>
                  ) : (
                    <>
                      <CardTitle className="flex items-center gap-2">
                        Documentos
                        <Badge variant="secondary">{stats?.total_documents ?? 0}</Badge>
                      </CardTitle>
                      <CardDescription>Total de boletines procesados</CardDescription>
                    </>
                  )}
                </CardHeader>
              </Card>

              <Card>
                <CardHeader>
                  {isLoading ? (
                    <>
                      <Skeleton className="h-8 w-32" />
                      <Skeleton className="h-4 w-48 mt-2" />
                    </>
                  ) : (
                    <>
                      <CardTitle className="flex items-center gap-2">
                        Chunks
                        <Badge variant="secondary">{stats?.total_chunks ?? 0}</Badge>
                      </CardTitle>
                      <CardDescription>Fragmentos indexados</CardDescription>
                    </>
                  )}
                </CardHeader>
              </Card>

              <Card>
                <CardHeader>
                  {isLoading ? (
                    <>
                      <Skeleton className="h-8 w-32" />
                      <Skeleton className="h-4 w-48 mt-2" />
                    </>
                  ) : (
                    <>
                      <CardTitle className="flex items-center gap-2">
                        Entidades
                        <Badge variant="secondary">{stats?.total_entities ?? 0}</Badge>
                      </CardTitle>
                      <CardDescription>Entidades extraídas</CardDescription>
                    </>
                  )}
                </CardHeader>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Estado del Sistema</CardTitle>
                <CardDescription>Configuración y componentes</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 font-mono text-sm">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-success">✓</Badge>
                    <span>Tailwind CSS configurado</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-success">✓</Badge>
                    <span>shadcn/ui componentes instalados</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-success">✓</Badge>
                    <span>Layout responsivo (AppShell + Nav)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-success">✓</Badge>
                    <span>Tema oscuro "Watcher"</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )

      case "/documentos":
        return (
          <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">Documentos</h1>
            <Card>
              <CardHeader>
                <CardTitle>Hub de Documentos</CardTitle>
                <CardDescription>Gestión de boletines oficiales</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  Funcionalidad en desarrollo - UI-2.2
                </p>
              </CardContent>
            </Card>
          </div>
        )

      case "/conocimiento":
        return (
          <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">Conocimiento</h1>
            <Card>
              <CardHeader>
                <CardTitle>Hub de Conocimiento</CardTitle>
                <CardDescription>Búsqueda semántica y grafo de entidades</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  Funcionalidad en desarrollo - UI-2.4, UI-2.5
                </p>
              </CardContent>
            </Card>
          </div>
        )

      case "/analisis":
        return (
          <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">Análisis</h1>
            <Card>
              <CardHeader>
                <CardTitle>Panel de Análisis</CardTitle>
                <CardDescription>Análisis presupuestario y anomalías</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  Funcionalidad en desarrollo - Futuras épicas
                </p>
              </CardContent>
            </Card>
          </div>
        )

      default:
        return <div>Página no encontrada</div>
    }
  }

  return (
    <AppShell currentPath={currentPath} onNavigate={setCurrentPath}>
      {getPageContent()}
    </AppShell>
  )
}

export default App
