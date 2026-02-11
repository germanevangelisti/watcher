import { useState, useCallback, useRef } from "react"
import ForceGraph2D from "react-force-graph-2d"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { FadeTransition } from "@/components/ui/fade-transition"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useKnowledgeGraph, useEntityTimeline } from "@/lib/api"
import { Network, User, Building2, Briefcase, FileText, Calendar, Filter, RefreshCw } from "lucide-react"

export function GraphPage() {
  const [maxNodes, setMaxNodes] = useState(50)
  const [minMentions, setMinMentions] = useState(3)
  const [selectedNode, setSelectedNode] = useState<any>(null)
  const graphRef = useRef<any>(null)

  const { data: graphData, isLoading, error, refetch } = useKnowledgeGraph({
    max_nodes: maxNodes,
    min_mentions: minMentions,
  })

  const { data: timeline, isLoading: timelineLoading } = useEntityTimeline(
    selectedNode?.id || ""
  )

  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node)
  }, [])

  const getNodeColor = (type: string) => {
    switch (type) {
      case "persona":
        return "#3b82f6" // blue
      case "organismo":
        return "#10b981" // green
      case "empresa":
        return "#f59e0b" // amber
      case "contrato":
        return "#8b5cf6" // purple
      default:
        return "#6b7280" // gray
    }
  }

  const getNodeIcon = (type: string) => {
    switch (type) {
      case "persona":
        return <User className="h-4 w-4" />
      case "organismo":
        return <Building2 className="h-4 w-4" />
      case "empresa":
        return <Briefcase className="h-4 w-4" />
      case "contrato":
        return <FileText className="h-4 w-4" />
      default:
        return null
    }
  }

  const getNodeTypeName = (type: string) => {
    const names: Record<string, string> = {
      persona: "Persona",
      organismo: "Organismo",
      empresa: "Empresa",
      contrato: "Contrato",
      monto: "Monto",
    }
    return names[type] || type
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Grafo de Conocimiento</h1>
        <p className="text-muted-foreground mt-2">
          Visualización de relaciones entre entidades
        </p>
      </div>

      <Tabs defaultValue="visualization" className="space-y-4">
        <TabsList>
          <TabsTrigger value="visualization">Visualización</TabsTrigger>
          <TabsTrigger value="stats">Estadísticas</TabsTrigger>
        </TabsList>

        <TabsContent value="visualization" className="space-y-4">
          {/* Controls */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Filter className="h-5 w-5" />
                    Filtros
                  </CardTitle>
                  <CardDescription>
                    Ajusta los parámetros de visualización
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => refetch()}
                  disabled={isLoading}
                  className="gap-2"
                >
                  <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
                  Recargar
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Nodos máximos</label>
                  <Input
                    type="number"
                    min="10"
                    max="200"
                    value={maxNodes}
                    onChange={(e) => setMaxNodes(parseInt(e.target.value) || 50)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Entre 10 y 200 nodos
                  </p>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Menciones mínimas</label>
                  <Input
                    type="number"
                    min="1"
                    max="20"
                    value={minMentions}
                    onChange={(e) => setMinMentions(parseInt(e.target.value) || 3)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Filtrar entidades con pocas menciones
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Legend */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Leyenda</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  <span className="text-sm">Personas</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500" />
                  <span className="text-sm">Organismos</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-amber-500" />
                  <span className="text-sm">Empresas</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-purple-500" />
                  <span className="text-sm">Contratos</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Graph Visualization with smooth transitions */}
          <FadeTransition
            isLoading={isLoading}
            skeleton={
              <Card>
                <CardContent className="p-0">
                  <Skeleton className="h-[600px] w-full" />
                </CardContent>
              </Card>
            }
          >
            {error ? (
              <Card className="border-danger">
                <CardHeader>
                  <CardTitle className="text-danger">Error</CardTitle>
                  <CardDescription>
                    No se pudo cargar el grafo de conocimiento
                  </CardDescription>
                </CardHeader>
              </Card>
            ) : graphData ? (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Network className="h-5 w-5" />
                      Visualización
                    </CardTitle>
                    <CardDescription>
                      {graphData.nodes.length} nodos • {graphData.links.length} conexiones
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <div className="border-t">
                  <ForceGraph2D
                    ref={graphRef}
                    graphData={graphData}
                    nodeLabel={(node: any) => `${node.label} (${node.mentions} menciones)`}
                    nodeColor={(node: any) => getNodeColor(node.type)}
                    nodeRelSize={6}
                    nodeVal={(node: any) => Math.sqrt(node.mentions) * 2}
                    onNodeClick={handleNodeClick}
                    linkColor={() => "#4b5563"}
                    linkWidth={1}
                    linkDirectionalParticles={2}
                    linkDirectionalParticleWidth={2}
                    backgroundColor="#09090b"
                    width={1200}
                    height={600}
                    cooldownTicks={100}
                    onEngineStop={() => graphRef.current?.zoomToFit(400)}
                  />
                </div>
              </CardContent>
            </Card>
            ) : null}
          </FadeTransition>
        </TabsContent>

        <TabsContent value="stats" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Estadísticas del Grafo</CardTitle>
              <CardDescription>
                Información sobre entidades y relaciones
              </CardDescription>
            </CardHeader>
            <CardContent>
              {graphData && (
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-4">
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Total Nodos</p>
                      <p className="text-2xl font-bold">{graphData.nodes.length}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Total Conexiones</p>
                      <p className="text-2xl font-bold">{graphData.links.length}</p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Menciones Totales</p>
                      <p className="text-2xl font-bold">
                        {graphData.nodes.reduce((sum: number, n: any) => sum + n.mentions, 0)}
                      </p>
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground">Densidad</p>
                      <p className="text-2xl font-bold">
                        {graphData.nodes.length > 0
                          ? ((graphData.links.length / (graphData.nodes.length * (graphData.nodes.length - 1))) * 100).toFixed(1)
                          : 0}%
                      </p>
                    </div>
                  </div>

                  <div className="border-t pt-4">
                    <h3 className="text-sm font-medium mb-3">Top 10 Entidades</h3>
                    <div className="space-y-2">
                      {graphData.nodes
                        .sort((a: any, b: any) => b.mentions - a.mentions)
                        .slice(0, 10)
                        .map((node: any, idx: number) => (
                          <div
                            key={node.id}
                            className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50 cursor-pointer"
                            onClick={() => setSelectedNode(node)}
                          >
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="w-8 justify-center">
                                #{idx + 1}
                              </Badge>
                              <div
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: getNodeColor(node.type) }}
                              />
                              <span className="text-sm font-medium">{node.label}</span>
                              <Badge variant="secondary" className="text-xs">
                                {getNodeTypeName(node.type)}
                              </Badge>
                            </div>
                            <Badge variant="outline">{node.mentions} menciones</Badge>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Entity Detail Modal */}
      <Dialog open={!!selectedNode} onOpenChange={() => setSelectedNode(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedNode && getNodeIcon(selectedNode.type)}
              {selectedNode?.label}
            </DialogTitle>
            <DialogDescription>
              {selectedNode && (
                <div className="flex items-center gap-2 mt-2">
                  <Badge>{getNodeTypeName(selectedNode.type)}</Badge>
                  <Badge variant="outline">{selectedNode.mentions} menciones</Badge>
                </div>
              )}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {timelineLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ) : timeline?.eventos && timeline.eventos.length > 0 ? (
              <div className="space-y-3">
                <h3 className="text-sm font-medium flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Timeline de apariciones
                </h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {timeline.eventos.map((evento: any, idx: number) => (
                    <div
                      key={idx}
                      className="border rounded-lg p-3 space-y-1 hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{evento.boletin_filename}</span>
                        <span className="text-xs text-muted-foreground">{evento.fecha}</span>
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {evento.contexto}
                      </p>
                      {evento.tipo_evento && (
                        <Badge variant="secondary" className="text-xs">
                          {evento.tipo_evento}
                        </Badge>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No hay información de timeline disponible para esta entidad
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
