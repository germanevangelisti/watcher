import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useDashboardStats } from "@/lib/api/hooks/use-dashboard-stats"
import { FileText, Database, Network, Upload, Search, BarChart3, AlertCircle } from "lucide-react"
import { Link } from "@tanstack/react-router"

export function DashboardPage() {
  const { data: stats, isLoading, error } = useDashboardStats()

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Watcher MVP v1.1</h1>
            <p className="text-muted-foreground mt-2 text-lg">
              Sistema de análisis de documentos oficiales con IA
            </p>
          </div>
          <Badge 
            variant={error ? "destructive" : "default"}
            className="h-8 px-4 text-sm"
          >
            {error ? "Desconectado" : "Sistema activo"}
          </Badge>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Card className="border-danger bg-danger/5">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-danger" />
              <CardTitle className="text-danger">Error de conexión</CardTitle>
            </div>
            <CardDescription>
              No se pudo conectar con el backend. Asegúrate de que el servidor esté corriendo en http://localhost:8001
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {/* Quick Stats Grid */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Documentos Procesados
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-10 w-24" />
            ) : (
              <>
                <div className="text-3xl font-bold">{stats?.total_documents ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Boletines oficiales indexados
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Fragmentos Indexados
            </CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-10 w-24" />
            ) : (
              <>
                <div className="text-3xl font-bold">{stats?.total_chunks ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Chunks para búsqueda semántica
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Entidades Extraídas
            </CardTitle>
            <Network className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-10 w-24" />
            ) : (
              <>
                <div className="text-3xl font-bold">{stats?.total_entities ?? 0}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Grafo de conocimiento
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Acciones Rápidas</CardTitle>
          <CardDescription>
            Accede a las funcionalidades principales del sistema
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Link to="/documentos">
              <Button variant="outline" className="w-full h-auto flex-col gap-2 py-4">
                <Upload className="h-6 w-6" />
                <div className="text-center">
                  <div className="font-semibold">Cargar Documento</div>
                  <div className="text-xs text-muted-foreground">Subir boletín oficial</div>
                </div>
              </Button>
            </Link>

            <Link to="/conocimiento/busqueda">
              <Button variant="outline" className="w-full h-auto flex-col gap-2 py-4">
                <Search className="h-6 w-6" />
                <div className="text-center">
                  <div className="font-semibold">Buscar</div>
                  <div className="text-xs text-muted-foreground">Búsqueda semántica</div>
                </div>
              </Button>
            </Link>

            <Link to="/conocimiento/grafo">
              <Button variant="outline" className="w-full h-auto flex-col gap-2 py-4">
                <Network className="h-6 w-6" />
                <div className="text-center">
                  <div className="font-semibold">Grafo</div>
                  <div className="text-xs text-muted-foreground">Visualizar entidades</div>
                </div>
              </Button>
            </Link>

            <Link to="/analisis">
              <Button variant="outline" className="w-full h-auto flex-col gap-2 py-4">
                <BarChart3 className="h-6 w-6" />
                <div className="text-center">
                  <div className="font-semibold">Análisis</div>
                  <div className="text-xs text-muted-foreground">Panel de métricas</div>
                </div>
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Two Column Layout */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* System Status */}
        <Card>
          <CardHeader>
            <CardTitle>Estado del Sistema</CardTitle>
            <CardDescription>Componentes y servicios</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-success" />
                  <span className="text-sm">Frontend v2</span>
                </div>
                <Badge variant="outline" className="bg-success/10 text-success">
                  Activo
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-success" />
                  <span className="text-sm">API Backend</span>
                </div>
                <Badge variant="outline" className={error ? "bg-danger/10 text-danger" : "bg-success/10 text-success"}>
                  {error ? "Desconectado" : "Activo"}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-success" />
                  <span className="text-sm">Vector Search</span>
                </div>
                <Badge variant="outline" className="bg-success/10 text-success">
                  ChromaDB
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-success" />
                  <span className="text-sm">Embeddings</span>
                </div>
                <Badge variant="outline" className="bg-success/10 text-success">
                  Google AI
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Actividad Reciente</CardTitle>
            <CardDescription>Últimas operaciones del sistema</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <FileText className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1 space-y-1">
                  <p className="text-sm font-medium">Sistema inicializado</p>
                  <p className="text-xs text-muted-foreground">
                    Dashboard v2 activo y funcional
                  </p>
                </div>
                <time className="text-xs text-muted-foreground">Ahora</time>
              </div>

              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
                  <Database className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="flex-1 space-y-1">
                  <p className="text-sm">
                    {stats?.total_documents ?? 0} documentos disponibles
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Listos para consulta
                  </p>
                </div>
              </div>

              {!error && stats && (stats.total_documents > 0 || stats.total_chunks > 0) && (
                <div className="flex items-start gap-4">
                  <div className="w-8 h-8 rounded-full bg-success/10 flex items-center justify-center flex-shrink-0">
                    <Network className="h-4 w-4 text-success" />
                  </div>
                  <div className="flex-1 space-y-1">
                    <p className="text-sm font-medium">Sistema operativo</p>
                    <p className="text-xs text-muted-foreground">
                      {stats.total_chunks} chunks indexados
                    </p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
