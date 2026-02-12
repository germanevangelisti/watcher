import { useState } from "react"
import { useParams, Link } from "@tanstack/react-router"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useBoletin, useBoletinContent, useBoletinAnalisis } from "@/lib/api"
import { ArrowLeft, FileText, Calendar, Database, CheckCircle2, Clock, ExternalLink, Maximize2, Upload, Download, RefreshCw, MapPin, AlertTriangle, Shield } from "lucide-react"
import dayjs from "dayjs"

export function BoletinDetail() {
  const { id } = useParams({ strict: false })
  const boletinId = id ? parseInt(id) : 0
  const [showFullText, setShowFullText] = useState(false)

  const { data: boletin, isLoading, error } = useBoletin(boletinId)
  const { data: content, isLoading: contentLoading } = useBoletinContent(boletin?.filename)
  const { data: analisis, isLoading: analisisLoading } = useBoletinAnalisis(boletinId)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (error || !boletin) {
    return (
      <div className="space-y-6">
        <Link to="/documentos">
          <Button variant="ghost" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Volver
          </Button>
        </Link>
        <Card className="border-danger">
          <CardHeader>
            <CardTitle className="text-danger">Error</CardTitle>
            <CardDescription>
              No se pudo cargar el documento. Verifica que el ID sea válido.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  const formattedDate = dayjs(boletin.date).format("DD/MM/YYYY")

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <Link to="/documentos">
            <Button variant="ghost" className="gap-2 -ml-2 mb-2">
              <ArrowLeft className="h-4 w-4" />
              Volver a documentos
            </Button>
          </Link>
          <h1 className="text-3xl font-bold tracking-tight">{boletin.filename}</h1>
          <p className="text-muted-foreground flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            {formattedDate} • Sección {boletin.section}
            {boletin.jurisdiccion_nombre && (
              <>
                {" • "}
                <MapPin className="h-3.5 w-3.5" />
                {boletin.jurisdiccion_nombre}
              </>
            )}
          </p>
        </div>
        <Badge 
          variant={boletin.processed ? "default" : "secondary"}
          className="flex items-center gap-1"
        >
          {boletin.processed ? (
            <>
              <CheckCircle2 className="h-3 w-3" />
              Procesado
            </>
          ) : (
            <>
              <Clock className="h-3 w-3" />
              Pendiente
            </>
          )}
        </Badge>
      </div>

      {/* Metadata Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Año</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{boletin.year}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Mes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{boletin.month}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Páginas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{boletin.total_pages || "N/A"}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Sección</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{boletin.section}</div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs Content */}
      <Tabs defaultValue="contenido" className="space-y-4">
        <TabsList>
          <TabsTrigger value="contenido">Contenido</TabsTrigger>
          <TabsTrigger value="analisis">Análisis</TabsTrigger>
          <TabsTrigger value="metadata">Metadata</TabsTrigger>
        </TabsList>

        <TabsContent value="contenido" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Vista previa del contenido</CardTitle>
                  <CardDescription>
                    {contentLoading ? "Cargando..." : `${content?.total_chars?.toLocaleString() || 0} caracteres`}
                  </CardDescription>
                </div>
                <Dialog open={showFullText} onOpenChange={setShowFullText}>
                  <DialogTrigger asChild>
                    <Button variant="outline" size="sm" className="gap-2">
                      <Maximize2 className="h-4 w-4" />
                      Texto completo
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                    <DialogHeader>
                      <DialogTitle>{boletin.filename}</DialogTitle>
                      <DialogDescription>
                        Texto completo del documento
                      </DialogDescription>
                    </DialogHeader>
                    {contentLoading ? (
                      <Skeleton className="h-96 w-full" />
                    ) : (
                      <pre className="text-xs font-mono whitespace-pre-wrap bg-muted p-4 rounded-lg">
                        {content?.text || "No hay contenido disponible"}
                      </pre>
                    )}
                  </DialogContent>
                </Dialog>
              </div>
            </CardHeader>
            <CardContent>
              {contentLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ) : (
                <div className="space-y-4">
                  <pre className="text-sm whitespace-pre-wrap bg-muted p-4 rounded-lg max-h-96 overflow-y-auto">
                    {content?.text?.substring(0, 2000) || "No hay contenido disponible"}
                    {content && content.text && content.text.length > 2000 && (
                      <span className="text-muted-foreground">
                        {"\n\n... (vista previa de 2000 caracteres)"}
                      </span>
                    )}
                  </pre>
                  
                  {boletin.pdf_path && (
                    <Button variant="outline" className="gap-2 w-full" asChild>
                      <a href={boletin.pdf_path} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="h-4 w-4" />
                        Abrir PDF original
                      </a>
                    </Button>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analisis" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Análisis del Documento</CardTitle>
              <CardDescription>
                Información extraída y procesada
              </CardDescription>
            </CardHeader>
            <CardContent>
              {analisisLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ) : analisis?.total > 0 ? (
                <div className="space-y-4">
                  {/* Stats */}
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Database className="h-4 w-4" />
                        Fragmentos analizados
                      </div>
                      <p className="text-2xl font-bold">{analisis.total}</p>
                      <p className="text-xs text-muted-foreground">
                        Actos normativos identificados
                      </p>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <FileText className="h-4 w-4" />
                        Entidades detectadas
                      </div>
                      <p className="text-2xl font-bold">
                        {new Set(analisis.analisis.map((a: { entidad_beneficiaria: string }) => a.entidad_beneficiaria).filter(Boolean)).size}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Organismos y entidades únicas
                      </p>
                    </div>
                  </div>

                  {/* Analysis items */}
                  <div className="space-y-3 mt-4">
                    <h4 className="text-sm font-medium text-muted-foreground">Detalle de análisis</h4>
                    {analisis.analisis.map((item: { id: number; categoria: string; entidad_beneficiaria: string; monto_estimado: string; riesgo: string; tipo_curro: string; accion_sugerida: string; fragmento: string }) => (
                      <Card key={item.id} className="border-muted">
                        <CardContent className="pt-4 pb-3 space-y-3">
                          <div className="flex items-start justify-between gap-4">
                            <div className="space-y-1 flex-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <Badge variant="outline" className="text-xs">
                                  {item.categoria}
                                </Badge>
                                <Badge 
                                  variant={item.riesgo === "ALTO" ? "destructive" : item.riesgo === "MEDIO" ? "default" : "secondary"}
                                  className="text-xs"
                                >
                                  {item.riesgo === "ALTO" && <AlertTriangle className="h-3 w-3 mr-1" />}
                                  {item.riesgo === "MEDIO" && <Shield className="h-3 w-3 mr-1" />}
                                  Riesgo {item.riesgo}
                                </Badge>
                              </div>
                              <p className="text-sm font-medium">{item.tipo_curro}</p>
                              <p className="text-xs text-muted-foreground">
                                Entidad: {item.entidad_beneficiaria}
                              </p>
                              {item.monto_estimado && item.monto_estimado !== "No especificado" && (
                                <p className="text-xs text-muted-foreground">
                                  Monto: <span className="font-mono font-medium text-foreground">{item.monto_estimado}</span>
                                </p>
                              )}
                            </div>
                          </div>
                          <div className="text-xs text-muted-foreground bg-muted p-2 rounded">
                            <p className="font-medium mb-1">Acción sugerida:</p>
                            <p>{item.accion_sugerida}</p>
                          </div>
                          <details className="text-xs">
                            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                              Ver fragmento original
                            </summary>
                            <pre className="mt-2 text-xs whitespace-pre-wrap bg-muted p-2 rounded max-h-40 overflow-y-auto">
                              {item.fragmento?.substring(0, 500)}
                              {item.fragmento && item.fragmento.length > 500 && "..."}
                            </pre>
                          </details>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Database className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">
                    {boletin.processed 
                      ? "No se encontraron análisis para este documento." 
                      : "El documento aún no ha sido procesado."}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="metadata" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Metadata del Documento</CardTitle>
              <CardDescription>
                Información técnica y de procesamiento
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">ID:</span>
                  <span className="col-span-2 font-mono">{boletin.id}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">Filename:</span>
                  <span className="col-span-2 font-mono break-all">{boletin.filename}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">Fecha:</span>
                  <span className="col-span-2">{formattedDate}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">Año/Mes:</span>
                  <span className="col-span-2">{boletin.year}/{boletin.month}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">Sección:</span>
                  <span className="col-span-2">{boletin.section} {boletin.seccion_nombre && <span className="text-muted-foreground">({boletin.seccion_nombre})</span>}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">Jurisdicción:</span>
                  <span className="col-span-2 flex items-center gap-1.5">
                    <MapPin className="h-3 w-3 text-muted-foreground" />
                    {boletin.jurisdiccion_nombre || "N/A"}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">Fuente:</span>
                  <span className="col-span-2 capitalize">{boletin.fuente || "N/A"}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">Origen:</span>
                  <span className="col-span-2">
                    <Badge variant="outline" className="gap-1 text-xs">
                      {boletin.origin === "uploaded" ? (
                        <><Upload className="h-3 w-3" /> Manual</>
                      ) : boletin.origin === "synced" ? (
                        <><RefreshCw className="h-3 w-3" /> Sync</>
                      ) : (
                        <><Download className="h-3 w-3" /> Descargado</>
                      )}
                    </Badge>
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">Estado:</span>
                  <span className="col-span-2">
                    {boletin.processed ? (
                      <Badge variant="default" className="gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Procesado
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="gap-1">
                        <Clock className="h-3 w-3" />
                        Pendiente
                      </Badge>
                    )}
                  </span>
                </div>
                {boletin.error_message && (
                  <div className="grid grid-cols-3 gap-2 py-2 border-b">
                    <span className="text-muted-foreground">Error:</span>
                    <span className="col-span-2 text-destructive text-xs">{boletin.error_message}</span>
                  </div>
                )}
                {boletin.processing_date && (
                  <div className="grid grid-cols-3 gap-2 py-2 border-b">
                    <span className="text-muted-foreground">Fecha procesamiento:</span>
                    <span className="col-span-2">{dayjs(boletin.processing_date).format("DD/MM/YYYY HH:mm")}</span>
                  </div>
                )}
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">Archivo:</span>
                  <span className="col-span-2">
                    {boletin.has_file ? (
                      <Badge variant="outline" className="gap-1 text-xs text-green-500 border-green-500/30">
                        <CheckCircle2 className="h-3 w-3" />
                        Disponible
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="gap-1 text-xs text-yellow-500 border-yellow-500/30">
                        <Clock className="h-3 w-3" />
                        No disponible
                      </Badge>
                    )}
                  </span>
                </div>
                {boletin.pdf_path && (
                  <div className="grid grid-cols-3 gap-2 py-2 border-b">
                    <span className="text-muted-foreground">Ruta archivo:</span>
                    <span className="col-span-2 font-mono text-xs break-all">{boletin.pdf_path}</span>
                  </div>
                )}
                {boletin.updated_at && (
                  <div className="grid grid-cols-3 gap-2 py-2 border-b">
                    <span className="text-muted-foreground">Última actualización:</span>
                    <span className="col-span-2">{dayjs(boletin.updated_at).format("DD/MM/YYYY HH:mm:ss")}</span>
                  </div>
                )}
                <div className="grid grid-cols-3 gap-2 py-2">
                  <span className="text-muted-foreground">Creado:</span>
                  <span className="col-span-2">{dayjs(boletin.created_at).format("DD/MM/YYYY HH:mm:ss")}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
