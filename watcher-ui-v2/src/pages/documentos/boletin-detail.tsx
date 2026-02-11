import { useState } from "react"
import { useParams, Link } from "@tanstack/react-router"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useBoletin, useBoletinContent } from "@/lib/api"
import { ArrowLeft, FileText, Calendar, Database, CheckCircle2, Clock, ExternalLink, Maximize2 } from "lucide-react"
import dayjs from "dayjs"

export function BoletinDetail() {
  const { id } = useParams({ strict: false })
  const boletinId = id ? parseInt(id) : 0
  const [showFullText, setShowFullText] = useState(false)

  const { data: boletin, isLoading, error } = useBoletin(boletinId)
  const { data: content, isLoading: contentLoading } = useBoletinContent(boletin?.filename)

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
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Database className="h-4 w-4" />
                      Fragmentos generados
                    </div>
                    <p className="text-2xl font-bold">-</p>
                    <p className="text-xs text-muted-foreground">
                      Chunks para búsqueda semántica
                    </p>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <FileText className="h-4 w-4" />
                      Entidades extraídas
                    </div>
                    <p className="text-2xl font-bold">-</p>
                    <p className="text-xs text-muted-foreground">
                      Organismos, personas, empresas
                    </p>
                  </div>
                </div>

                <p className="text-sm text-muted-foreground">
                  Funcionalidad completa en desarrollo
                </p>
              </div>
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
                  <span className="col-span-2">{boletin.section}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">Procesado:</span>
                  <span className="col-span-2">
                    {boletin.processed ? (
                      <Badge variant="default" className="gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Sí
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="gap-1">
                        <Clock className="h-3 w-3" />
                        No
                      </Badge>
                    )}
                  </span>
                </div>
                {boletin.processing_date && (
                  <div className="grid grid-cols-3 gap-2 py-2 border-b">
                    <span className="text-muted-foreground">Fecha procesamiento:</span>
                    <span className="col-span-2">{dayjs(boletin.processing_date).format("DD/MM/YYYY HH:mm")}</span>
                  </div>
                )}
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">Total páginas:</span>
                  <span className="col-span-2">{boletin.total_pages || "N/A"}</span>
                </div>
                {boletin.file_hash && (
                  <div className="grid grid-cols-3 gap-2 py-2 border-b">
                    <span className="text-muted-foreground">File hash:</span>
                    <span className="col-span-2 font-mono text-xs break-all">{boletin.file_hash}</span>
                  </div>
                )}
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">PDF path:</span>
                  <span className="col-span-2 font-mono text-xs break-all">{boletin.pdf_path || "N/A"}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 py-2 border-b">
                  <span className="text-muted-foreground">TXT path:</span>
                  <span className="col-span-2 font-mono text-xs break-all">{boletin.txt_path || "N/A"}</span>
                </div>
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
