import { useState, useMemo, useEffect } from "react"
import { useParams, Link } from "@tanstack/react-router"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useBoletin, useBoletinContent, useBoletinAnalisis } from "@/lib/api"
import apiClient from "@/lib/api/client"
import { ArrowLeft, FileText, Calendar, Database, CheckCircle2, Clock, Maximize2, Upload, Download, RefreshCw, MapPin, AlertTriangle, Shield, Filter, Gavel, Building2, DollarSign, BookOpen, Loader2 } from "lucide-react"
import dayjs from "dayjs"

// Types for analysis items (supports both v1 and v2)
interface AIUSummary {
  total_aius: number
  by_type: Record<string, number>
}

interface AnalisisItem {
  id: number
  fragmento: string
  categoria: string
  entidad_beneficiaria: string
  monto_estimado: string
  riesgo: string
  tipo_curro: string
  accion_sugerida: string
  // v2 fields
  tipo_acto?: string | null
  numero_acto?: string | null
  organismo?: string | null
  beneficiarios?: string[]
  montos?: string[]
  monto_numerico?: number | null
  descripcion?: string | null
  motivo_riesgo?: string | null
  // Adversarial verification fields (Phases II + IV)
  aiu_summary_json?: AIUSummary | null
  firewall_score?: number | null
}

function formatCurrency(value: number): string {
  if (value >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(1).replace('.0', '')}B`
  }
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1).replace('.0', '')}M`
  }
  return `$${value.toLocaleString("es-AR", { maximumFractionDigits: 0 })}`
}

function formatCurrencyFull(value: number): string {
  return `$${value.toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const TIPO_ACTO_LABELS: Record<string, string> = {
  decreto: "Decreto",
  resolucion: "Resolución",
  licitacion: "Licitación",
  designacion: "Designación",
  subsidio: "Subsidio",
  transferencia: "Transferencia",
  otro: "Otro",
}

const TIPO_ACTO_ICONS: Record<string, typeof Gavel> = {
  decreto: Gavel,
  resolucion: FileText,
  licitacion: Building2,
  designacion: Shield,
  subsidio: Download,
  transferencia: RefreshCw,
  otro: FileText,
}

function getRiesgoVariant(riesgo: string): "destructive" | "default" | "secondary" | "outline" {
  const r = riesgo.toLowerCase()
  if (r === "alto") return "destructive"
  if (r === "medio") return "default"
  if (r === "bajo") return "secondary"
  return "outline" // informativo
}

function getRiesgoLabel(riesgo: string): string {
  const r = riesgo.toLowerCase()
  if (r === "informativo") return "Informativo"
  return `Riesgo ${r.charAt(0).toUpperCase() + r.slice(1)}`
}

export function BoletinDetail() {
  const { id } = useParams({ strict: false })
  const boletinId = id ? parseInt(id) : 0
  const [showFullText, setShowFullText] = useState(false)
  const [riesgoFilter, setRiesgoFilter] = useState<string>("all")

  // PDF fragment modal state
  const [pdfModal, setPdfModal] = useState<{
    open: boolean
    loading: boolean
    pageNumber: number | null
    totalPages: number
    found: boolean
    analisisId: number | null
    blobUrl: string | null
  }>({ open: false, loading: false, pageNumber: null, totalPages: 0, found: false, analisisId: null, blobUrl: null })

  // Content tab PDF view state
  const [contentView, setContentView] = useState<'text' | 'pdf'>('text')
  const [contentPdfUrl, setContentPdfUrl] = useState<string | null>(null)
  const [contentPdfLoading, setContentPdfLoading] = useState(false)

  // Clean up blob URLs on unmount
  useEffect(() => {
    return () => {
      if (pdfModal.blobUrl) URL.revokeObjectURL(pdfModal.blobUrl)
      if (contentPdfUrl) URL.revokeObjectURL(contentPdfUrl)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function closePdfModal() {
    setPdfModal(s => {
      if (s.blobUrl) URL.revokeObjectURL(s.blobUrl)
      return { ...s, open: false, blobUrl: null }
    })
  }

  const { data: boletin, isLoading, error } = useBoletin(boletinId)
  const { data: content, isLoading: contentLoading } = useBoletinContent(boletin?.filename)
  const { data: analisis, isLoading: analisisLoading } = useBoletinAnalisis(boletinId)

  // Relative API path for PDF — goes through Vite proxy (same-origin, no CORS)
  const pdfApiPath = boletin?.filename ? `/api/v1/documentos/pdf/${boletin.filename}` : null

  // Load PDF blob for the content tab viewer
  async function switchToContentPdf() {
    if (!pdfApiPath) return
    setContentView('pdf')
    if (contentPdfUrl) return // already loaded
    setContentPdfLoading(true)
    try {
      const blob = await fetch(pdfApiPath).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.blob()
      })
      setContentPdfUrl(URL.createObjectURL(blob))
    } catch (e) {
      console.error('PDF viewer load failed:', e)
      setContentView('text')
    } finally {
      setContentPdfLoading(false)
    }
  }

  // Programmatic download via Vite proxy (same-origin blob)
  async function downloadPdf() {
    if (!pdfApiPath || !boletin?.filename) return
    try {
      const blob = await fetch(pdfApiPath).then(r => r.blob())
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = boletin.filename
      a.click()
      setTimeout(() => URL.revokeObjectURL(a.href), 1000)
    } catch (e) {
      console.error('Download failed:', e)
    }
  }

  // Open PDF modal at the page containing a specific analysis fragment
  async function openPdfAtFragment(item: AnalisisItem) {
    if (!pdfApiPath) return
    setPdfModal({ open: true, loading: true, pageNumber: null, totalPages: 0, found: false, analisisId: item.id, blobUrl: null })

    // Run both in parallel; either can fail without blocking the other
    const [locationResult, pdfResult] = await Promise.allSettled([
      apiClient.get<{ found: boolean; page_number: number | null; total_pages: number }>(
        `/boletines/${boletinId}/analisis/${item.id}/fragment-location`
      ),
      fetch(pdfApiPath).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.blob()
      }),
    ])

    if (locationResult.status === 'rejected') console.error('Fragment location:', locationResult.reason)
    if (pdfResult.status === 'rejected') console.error('PDF fetch:', pdfResult.reason)

    const location = locationResult.status === 'fulfilled' ? locationResult.value.data : null
    const pdfBlob = pdfResult.status === 'fulfilled' ? pdfResult.value : null
    const blobUrl = pdfBlob ? URL.createObjectURL(pdfBlob) : null

    setPdfModal({
      open: true, loading: false,
      pageNumber: location?.page_number ?? null,
      totalPages: location?.total_pages ?? 0,
      found: location?.found ?? false,
      analisisId: item.id,
      blobUrl,
    })
  }

  // Filter and count analysis items by risk level, compute total montos
  const { filteredItems, riesgoCounts, totalMontoNumerico, actosConMonto } = useMemo(() => {
    const items: AnalisisItem[] = analisis?.analisis || []
    const counts: Record<string, number> = { all: items.length, alto: 0, medio: 0, bajo: 0, informativo: 0 }
    let montoSum = 0
    let conMonto = 0
    for (const item of items) {
      const r = (item.riesgo || "informativo").toLowerCase()
      counts[r] = (counts[r] || 0) + 1
      if (item.monto_numerico && item.monto_numerico > 0) {
        montoSum += item.monto_numerico
        conMonto++
      }
    }
    const filtered = riesgoFilter === "all"
      ? items
      : items.filter(item => (item.riesgo || "informativo").toLowerCase() === riesgoFilter)
    return { filteredItems: filtered, riesgoCounts: counts, totalMontoNumerico: montoSum, actosConMonto: conMonto }
  }, [analisis, riesgoFilter])

  // Aggregate adversarial verification data from analisis items
  const verificationData = useMemo(() => {
    const items: AnalisisItem[] = analisis?.analisis || []
    const itemsWithAIU = items.filter(item => item.aiu_summary_json != null)
    const itemsWithFirewall = items.filter(item => item.firewall_score != null)

    const totalAIUs = itemsWithAIU.reduce((sum, item) => sum + (item.aiu_summary_json!.total_aius), 0)
    const byType: Record<string, number> = {}
    for (const item of itemsWithAIU) {
      for (const [type, count] of Object.entries(item.aiu_summary_json!.by_type)) {
        byType[type] = (byType[type] || 0) + count
      }
    }
    const avgFirewall = itemsWithFirewall.length
      ? itemsWithFirewall.reduce((sum, item) => sum + item.firewall_score!, 0) / itemsWithFirewall.length
      : null
    const flaggedItems = itemsWithFirewall.filter(item => item.firewall_score! < 1.0)
    const hasData = itemsWithAIU.length > 0 || itemsWithFirewall.length > 0

    return { totalAIUs, byType, avgFirewall, flaggedItems, itemsWithAIU, hasData, allItems: items }
  }, [analisis])

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
          <TabsTrigger value="verificacion" className="flex items-center gap-1">
            <Shield className="h-4 w-4" />
            Verificación
          </TabsTrigger>
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
                <div className="flex items-center gap-2">
                  {boletin.pdf_path && (
                    <div className="flex items-center rounded-md border overflow-hidden">
                      <Button
                        variant={contentView === 'text' ? "default" : "ghost"}
                        size="sm"
                        className="rounded-none h-8 text-xs px-3"
                        onClick={() => setContentView('text')}
                      >
                        <FileText className="h-3.5 w-3.5 mr-1.5" />
                        Texto
                      </Button>
                      <Button
                        variant={contentView === 'pdf' ? "default" : "ghost"}
                        size="sm"
                        className="rounded-none h-8 text-xs px-3 border-l"
                        onClick={switchToContentPdf}
                      >
                        {contentPdfLoading ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <BookOpen className="h-3.5 w-3.5 mr-1.5" />}
                        PDF
                      </Button>
                    </div>
                  )}
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
              </div>
            </CardHeader>
            <CardContent>
              {contentView === 'pdf' ? (
                contentPdfLoading ? (
                  <div className="flex items-center justify-center h-[600px] text-muted-foreground gap-2">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Cargando PDF…
                  </div>
                ) : contentPdfUrl ? (
                  <iframe
                    src={contentPdfUrl}
                    className="w-full border-0 rounded-lg"
                    style={{ height: "600px" }}
                    title="PDF viewer"
                  />
                ) : (
                  <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
                    No se pudo cargar el PDF.
                  </div>
                )
              ) : contentLoading ? (
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
                    <Button variant="outline" className="gap-2 w-full" onClick={downloadPdf}>
                      <Download className="h-4 w-4" />
                      Descargar archivo
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
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Análisis del Documento</CardTitle>
                  <CardDescription>
                    Actos administrativos extraídos y evaluados
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {!boletin.processed ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm font-medium">Documento pendiente de procesamiento</p>
                  <p className="text-xs mt-1">
                    El análisis estará disponible una vez que el documento sea procesado por el pipeline.
                  </p>
                </div>
              ) : analisisLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ) : analisis?.total > 0 ? (
                <div className="space-y-4">
                  {/* Stats row */}
                  <div className="grid gap-3 grid-cols-2 md:grid-cols-5">
                    <div className="space-y-1 text-center p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-bold">{analisis.total}</p>
                      <p className="text-xs text-muted-foreground">Actos totales</p>
                    </div>
                    <div className="space-y-1 text-center p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-bold">
                        {new Set(
                          analisis.analisis.flatMap((a: AnalisisItem) => 
                            a.organismo ? [a.organismo] : a.entidad_beneficiaria ? [a.entidad_beneficiaria] : []
                          ).filter(Boolean)
                        ).size}
                      </p>
                      <p className="text-xs text-muted-foreground">Organismos</p>
                    </div>
                    <div className="space-y-1 text-center p-3 rounded-lg bg-emerald-500/10">
                      <p className="text-xl font-bold text-emerald-400 font-mono">
                        {totalMontoNumerico > 0 ? formatCurrency(totalMontoNumerico) : "-"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {actosConMonto > 0 ? `Montos (${actosConMonto} actos)` : "Sin montos"}
                      </p>
                    </div>
                    <div className="space-y-1 text-center p-3 rounded-lg bg-red-500/10">
                      <p className="text-2xl font-bold text-red-500">{riesgoCounts.alto || 0}</p>
                      <p className="text-xs text-muted-foreground">Riesgo alto</p>
                    </div>
                    <div className="space-y-1 text-center p-3 rounded-lg bg-yellow-500/10">
                      <p className="text-2xl font-bold text-yellow-500">{riesgoCounts.medio || 0}</p>
                      <p className="text-xs text-muted-foreground">Riesgo medio</p>
                    </div>
                  </div>

                  {/* Risk filter */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <Filter className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">Filtrar:</span>
                    {[
                      { key: "all", label: "Todos", count: riesgoCounts.all },
                      { key: "alto", label: "Alto", count: riesgoCounts.alto },
                      { key: "medio", label: "Medio", count: riesgoCounts.medio },
                      { key: "bajo", label: "Bajo", count: riesgoCounts.bajo },
                      { key: "informativo", label: "Informativo", count: riesgoCounts.informativo },
                    ].filter(f => f.count > 0).map(f => (
                      <Button
                        key={f.key}
                        variant={riesgoFilter === f.key ? "default" : "outline"}
                        size="sm"
                        className="h-7 text-xs gap-1"
                        onClick={() => setRiesgoFilter(f.key)}
                      >
                        {f.label} ({f.count})
                      </Button>
                    ))}
                  </div>

                  {/* Analysis items */}
                  <div className="space-y-3">
                    {filteredItems.map((item: AnalisisItem) => {
                      const isV2 = !!item.tipo_acto
                      const tipoLabel = isV2 ? (TIPO_ACTO_LABELS[item.tipo_acto!] || item.tipo_acto) : item.categoria
                      const TipoIcon = isV2 ? (TIPO_ACTO_ICONS[item.tipo_acto!] || FileText) : FileText
                      const description = item.descripcion || item.tipo_curro || "Sin descripción"
                      const organismo = item.organismo || item.entidad_beneficiaria || "No especificado"
                      const montos = item.montos?.length ? item.montos : (item.monto_estimado && item.monto_estimado !== "No especificado" ? [item.monto_estimado] : [])
                      const beneficiarios = item.beneficiarios?.length ? item.beneficiarios : []
                      const riesgo = (item.riesgo || "informativo").toLowerCase()

                      return (
                        <Card key={item.id} className={riesgo === "alto" ? "border-red-500/30" : riesgo === "medio" ? "border-yellow-500/30" : "border-muted"}>
                          <CardContent className="pt-4 pb-3 space-y-3">
                            {/* Header: tipo_acto badge + riesgo badge + numero */}
                            <div className="flex items-start justify-between gap-4">
                              <div className="space-y-1.5 flex-1">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <Badge variant="outline" className="text-xs gap-1">
                                    <TipoIcon className="h-3 w-3" />
                                    {tipoLabel}
                                  </Badge>
                                  {item.numero_acto && (
                                    <span className="text-xs font-mono text-muted-foreground">
                                      {item.numero_acto}
                                    </span>
                                  )}
                                  <Badge variant={getRiesgoVariant(riesgo)} className="text-xs">
                                    {riesgo === "alto" && <AlertTriangle className="h-3 w-3 mr-1" />}
                                    {riesgo === "medio" && <Shield className="h-3 w-3 mr-1" />}
                                    {getRiesgoLabel(riesgo)}
                                  </Badge>
                                </div>
                                
                                {/* Description */}
                                <p className="text-sm font-medium">{description}</p>
                                
                                {/* Organismo */}
                                <p className="text-xs text-muted-foreground flex items-center gap-1">
                                  <Building2 className="h-3 w-3" />
                                  {organismo}
                                </p>

                                {/* Beneficiarios (if any) */}
                                {beneficiarios.length > 0 && (
                                  <p className="text-xs text-muted-foreground">
                                    Beneficiarios: {beneficiarios.join(", ")}
                                  </p>
                                )}
                                
                                {/* Montos */}
                                {(item.monto_numerico || montos.length > 0) && (
                                  <div className="flex items-center gap-2 text-xs">
                                    <DollarSign className="h-3 w-3 text-emerald-400" />
                                    {item.monto_numerico && item.monto_numerico > 0 ? (
                                      <span className="font-mono font-bold text-emerald-400" title={formatCurrencyFull(item.monto_numerico)}>
                                        {formatCurrency(item.monto_numerico)}
                                      </span>
                                    ) : null}
                                    {montos.length > 0 && (
                                      <span className="text-muted-foreground truncate" title={montos.join(", ")}>
                                        {montos.length === 1 ? montos[0] : `${montos.length} montos`}
                                      </span>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* Motivo riesgo (if not informativo) */}
                            {item.motivo_riesgo && riesgo !== "informativo" && (
                              <div className={`text-xs p-2 rounded border ${
                                riesgo === "alto" ? "bg-red-500/10 border-red-500/20" :
                                riesgo === "medio" ? "bg-yellow-500/10 border-yellow-500/20" :
                                "bg-blue-500/10 border-blue-500/20"
                              }`}>
                                <p className="font-medium mb-0.5">Motivo del riesgo:</p>
                                <p>{item.motivo_riesgo}</p>
                              </div>
                            )}

                            {/* Accion sugerida (if present and not informativo) */}
                            {item.accion_sugerida && riesgo !== "informativo" && (
                              <div className="text-xs text-muted-foreground bg-muted p-2 rounded">
                                <p className="font-medium mb-0.5">Acción sugerida:</p>
                                <p>{item.accion_sugerida}</p>
                              </div>
                            )}

                            {/* Expandable fragment + Ver en PDF */}
                            <div className="space-y-1.5">
                              <details className="text-xs">
                                <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                                  Ver fragmento original
                                </summary>
                                <pre className="mt-2 text-xs whitespace-pre-wrap bg-muted p-2 rounded max-h-64 overflow-y-auto">
                                  {item.fragmento}
                                </pre>
                              </details>
                              {boletin?.pdf_path && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 text-xs gap-1 text-muted-foreground hover:text-foreground px-1"
                                  onClick={() => openPdfAtFragment(item)}
                                >
                                  <BookOpen className="h-3 w-3" />
                                  Ver en PDF
                                </Button>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      )
                    })}
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

        <TabsContent value="verificacion">
          {analisisLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : !verificationData.hasData ? (
            <div className="py-12 text-center text-muted-foreground text-sm">
              Este boletín no tiene datos de verificación adversarial. Procesalo primero con el pipeline.
            </div>
          ) : (
            <div className="space-y-5">
              {/* Alert banner for flagged items */}
              {verificationData.flaggedItems.length > 0 && (
                <div className="flex items-center gap-2 p-3 rounded-md bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-sm">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  {verificationData.flaggedItems.length} acto(s) con referencias que no pudieron verificarse en la base de datos.
                </div>
              )}

              {/* Summary cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="rounded-lg border p-3 text-center">
                  <div className={`text-2xl font-bold ${
                    verificationData.avgFirewall == null ? "text-muted-foreground" :
                    verificationData.avgFirewall >= 0.85 ? "text-green-400" :
                    verificationData.avgFirewall >= 0.70 ? "text-yellow-400" : "text-red-400"
                  }`}>
                    {verificationData.avgFirewall != null ? `${Math.round(verificationData.avgFirewall * 100)}%` : "—"}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">Firewall Score</div>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <div className="text-2xl font-bold">{verificationData.totalAIUs}</div>
                  <div className="text-xs text-muted-foreground mt-1">AIUs totales</div>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <div className="text-2xl font-bold">{verificationData.itemsWithAIU.length}</div>
                  <div className="text-xs text-muted-foreground mt-1">Actos analizados</div>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <div className={`text-2xl font-bold ${verificationData.flaggedItems.length > 0 ? "text-yellow-400" : "text-green-400"}`}>
                    {verificationData.flaggedItems.length}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">Con alertas</div>
                </div>
              </div>

              {/* AIU by type breakdown */}
              {Object.keys(verificationData.byType).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium mb-2 text-muted-foreground uppercase tracking-wider">AIUs por tipo de afirmación</h3>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(verificationData.byType)
                      .sort(([, a], [, b]) => b - a)
                      .map(([type, count]) => (
                        <div key={type} className="flex items-center gap-1.5 rounded-md border bg-muted/30 px-2.5 py-1.5 text-xs">
                          <span className="capitalize text-muted-foreground">{type.replace("_", " ")}</span>
                          <span className="font-bold text-foreground">{count}</span>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {/* Per-acto detail table */}
              {verificationData.allItems.some(i => i.aiu_summary_json || i.firewall_score != null) && (
                <div>
                  <h3 className="text-sm font-medium mb-2 text-muted-foreground uppercase tracking-wider">Detalle por acto</h3>
                  <div className="rounded-md border overflow-auto">
                    <table className="w-full text-xs">
                      <thead className="border-b bg-muted/30">
                        <tr>
                          <th className="px-3 py-2 text-left font-medium">Acto</th>
                          <th className="px-3 py-2 text-center font-medium w-16">AIUs</th>
                          <th className="px-3 py-2 text-center font-medium w-24">Firewall</th>
                          <th className="px-3 py-2 text-left font-medium">Tipos de afirmaciones</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {verificationData.allItems
                          .filter(item => item.aiu_summary_json || item.firewall_score != null)
                          .map(item => {
                            const score = item.firewall_score ?? 1.0
                            const scoreColor = score >= 0.85 ? "text-green-400" : score >= 0.70 ? "text-yellow-400" : "text-red-400"
                            const label = item.numero_acto
                              ? `${TIPO_ACTO_LABELS[item.tipo_acto || ""] || item.tipo_acto || ""} ${item.numero_acto}`.trim()
                              : item.descripcion?.slice(0, 55) || `Acto #${item.id}`
                            return (
                              <tr key={item.id} className="hover:bg-muted/20 transition-colors">
                                <td className="px-3 py-2 max-w-[220px]">
                                  <span className="line-clamp-2 leading-tight" title={label}>{label}</span>
                                </td>
                                <td className="px-3 py-2 text-center font-mono">
                                  {item.aiu_summary_json?.total_aius ?? "—"}
                                </td>
                                <td className={`px-3 py-2 text-center font-mono font-medium ${scoreColor}`}>
                                  {item.firewall_score != null ? `${Math.round(score * 100)}%` : "—"}
                                </td>
                                <td className="px-3 py-2">
                                  <div className="flex flex-wrap gap-1">
                                    {Object.entries(item.aiu_summary_json?.by_type || {}).map(([type, count]) => (
                                      <span key={type} className="bg-muted rounded px-1 py-0.5 text-muted-foreground">
                                        {type.replace("_", " ")}: <strong>{count}</strong>
                                      </span>
                                    ))}
                                  </div>
                                </td>
                              </tr>
                            )
                          })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* PDF viewer modal */}
      <Dialog open={pdfModal.open} onOpenChange={(open) => { if (!open) closePdfModal() }}>
        <DialogContent className="max-w-5xl h-[90vh] flex flex-col p-0">
          <DialogHeader className="px-6 pt-5 pb-3 border-b shrink-0">
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="h-4 w-4" />
              {boletin?.filename}
            </DialogTitle>
            <DialogDescription>
              {pdfModal.loading ? (
                <span className="flex items-center gap-1.5">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Cargando PDF y buscando fragmento…
                </span>
              ) : pdfModal.found ? (
                `Página ${pdfModal.pageNumber} de ${pdfModal.totalPages} — fragmento localizado`
              ) : pdfModal.totalPages > 0 ? (
                `Fragmento no localizado automáticamente — mostrando desde página 1 (${pdfModal.totalPages} pág. total)`
              ) : (
                "Visualizando PDF"
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 min-h-0">
            {pdfModal.loading ? (
              <div className="flex items-center justify-center h-full text-muted-foreground gap-2">
                <Loader2 className="h-5 w-5 animate-spin" />
                Cargando…
              </div>
            ) : pdfModal.blobUrl ? (
              <iframe
                src={`${pdfModal.blobUrl}#page=${pdfModal.pageNumber ?? 1}`}
                className="w-full h-full border-0"
                title="PDF viewer"
              />
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                No se pudo cargar el PDF.
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
