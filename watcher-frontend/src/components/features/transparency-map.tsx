import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { useTransparencyOverview } from "@/lib/api/hooks/use-transparency"
import type { JurisdictionLevel, JurisdictionSummary } from "@/lib/api/hooks/use-transparency"
import { toApplicableLaw, type ApplicableLaw } from "@/lib/applicable-law"
import { fileTypeRows, legalTypeRows, type FileTypeInfo } from "@/lib/file-type"
import { getJurisdictionLevel, JURISDICTION_LEVEL_LABEL } from "@/lib/jurisdiction-level"
import { MapPin, Building2, Landmark, FileCheck, FileX, FileDown, ChevronDown, ChevronRight, Scale, AlertTriangle, ExternalLink } from "lucide-react"
import { useState } from "react"
import { cn } from "@/lib/utils"

function getJurisdictionIcon(level: JurisdictionLevel) {
  switch (level) {
    case "nacion":
      return <Landmark className="h-5 w-5" />
    case "provincia":
      return <Building2 className="h-5 w-5" />
    default:
      return <MapPin className="h-5 w-5" />
  }
}

function getCoverageColor(coverage: number): string {
  if (coverage >= 75) return "text-green-500"
  if (coverage >= 40) return "text-yellow-500"
  return "text-red-500"
}

function getCoverageBg(coverage: number): string {
  if (coverage >= 75) return "bg-green-500"
  if (coverage >= 40) return "bg-yellow-500"
  return "bg-red-500"
}

/**
 * Una ley aplicable: link a la fuente oficial si existe, y si no el nombre con
 * el estado "sin URL". Nunca se fabrica un href para una ley sin fuente.
 */
function LawBadge({ law }: { law: ApplicableLaw }) {
  const url = law.official_url?.trim()
  if (!url) {
    return (
      <Badge variant="secondary" className="text-xs font-normal" data-testid="law-sin-url">
        <Scale className="h-3 w-3 mr-1 shrink-0" />
        {law.name}
        <span className="ml-1 text-muted-foreground">sin URL</span>
      </Badge>
    )
  }
  return (
    <Badge variant="secondary" className="text-xs font-normal">
      <Scale className="h-3 w-3 mr-1 shrink-0" />
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        data-testid="law-link"
      >
        {law.name}
        <ExternalLink className="h-3 w-3 ml-1 inline opacity-70" aria-hidden="true" />
        <span className="sr-only"> (abre en pestaña nueva)</span>
      </a>
    </Badge>
  )
}

function JurisdictionCard({
  jurisdiction,
  taxonomy,
}: {
  jurisdiction: JurisdictionSummary
  taxonomy?: FileTypeInfo[] | null
}) {
  const [expanded, setExpanded] = useState(false)
  const level = getJurisdictionLevel(jurisdiction)
  // Eje primario: tipo de archivo. Sin `by_file_type` (backend anterior a 1.1.0)
  // se cae al eje legal de siempre — el contrato viejo sigue funcionando.
  const usesFileTypeAxis = Object.keys(jurisdiction.by_file_type ?? {}).length > 0
  const rows = usesFileTypeAxis
    ? fileTypeRows(jurisdiction.by_file_type, taxonomy)
    : legalTypeRows(jurisdiction.by_type)

  return (
    <div
      data-testid={`jurisdiction-${jurisdiction.jurisdiction_code}`}
      className={cn(
        "rounded-lg border p-4 transition-colors hover:bg-muted/30",
        level === "nacion" && "border-blue-500/30 bg-blue-500/5",
        level === "provincia" && "border-purple-500/30 bg-purple-500/5",
        level === "municipio" && "border-orange-500/30 bg-orange-500/5"
      )}
    >
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className={cn(
            "p-2 rounded-lg",
            level === "nacion" && "bg-blue-500/10 text-blue-500",
            level === "provincia" && "bg-purple-500/10 text-purple-500",
            level === "municipio" && "bg-orange-500/10 text-orange-500"
          )}>
            {getJurisdictionIcon(level)}
          </div>
          <div>
            <h4 className="font-semibold text-sm">{jurisdiction.jurisdiction_name}</h4>
            <p className="text-xs text-muted-foreground" data-testid="jurisdiction-level">
              {JURISDICTION_LEVEL_LABEL[level]}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Coverage bar */}
          <div className="flex items-center gap-2">
            <div className="w-24 h-2 rounded-full bg-muted overflow-hidden">
              <div
                className={cn("h-full rounded-full transition-all", getCoverageBg(jurisdiction.coverage_percentage))}
                style={{ width: `${Math.min(100, jurisdiction.coverage_percentage)}%` }}
              />
            </div>
            <span className={cn("text-sm font-bold tabular-nums", getCoverageColor(jurisdiction.coverage_percentage))}>
              {jurisdiction.coverage_percentage.toFixed(0)}%
            </span>
          </div>

          {/* Status badges */}
          <div className="hidden sm:flex items-center gap-1.5">
            <Badge variant="outline" className="gap-1 text-xs bg-green-500/10 text-green-600 border-green-500/20">
              <FileCheck className="h-3 w-3" />
              {jurisdiction.processed}
            </Badge>
            <Badge variant="outline" className="gap-1 text-xs bg-blue-500/10 text-blue-600 border-blue-500/20">
              <FileDown className="h-3 w-3" />
              {jurisdiction.downloaded}
            </Badge>
            <Badge variant="outline" className="gap-1 text-xs bg-red-500/10 text-red-600 border-red-500/20">
              <FileX className="h-3 w-3" />
              {jurisdiction.missing}
            </Badge>
          </div>

          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="mt-4 pt-4 border-t space-y-3">
          {/* Status summary for mobile */}
          <div className="sm:hidden flex items-center gap-2 flex-wrap">
            <Badge variant="outline" className="gap-1 text-xs bg-green-500/10 text-green-600 border-green-500/20">
              <FileCheck className="h-3 w-3" />
              {jurisdiction.processed} procesados
            </Badge>
            <Badge variant="outline" className="gap-1 text-xs bg-blue-500/10 text-blue-600 border-blue-500/20">
              <FileDown className="h-3 w-3" />
              {jurisdiction.downloaded} descargados
            </Badge>
            <Badge variant="outline" className="gap-1 text-xs bg-red-500/10 text-red-600 border-red-500/20">
              <FileX className="h-3 w-3" />
              {jurisdiction.missing} faltantes
            </Badge>
          </div>

          {/* Laws */}
          {(jurisdiction.applicable_laws?.length ?? 0) > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1.5">Leyes aplicables:</p>
              <div className="flex flex-wrap gap-1.5" data-testid="applicable-laws">
                {jurisdiction.applicable_laws.map((raw, i) => (
                  <LawBadge key={i} law={toApplicableLaw(raw)} />
                ))}
              </div>
            </div>
          )}

          {/* Documents by type — eje primario: tipo de archivo */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1.5" data-testid="by-type-heading">
              {usesFileTypeAxis ? "Documentos por tipo de archivo:" : "Documentos por tipo (categoría legal):"}
            </p>
            {rows.length === 0 ? (
              <p className="text-xs text-muted-foreground" data-testid="by-type-empty">
                Sin documentos en el inventario para esta jurisdicción. Sincronizá el inventario
                (POST /api/v1/compliance/documents/sync).
              </p>
            ) : (
              <div
                className="grid gap-2 sm:grid-cols-2"
                data-testid={usesFileTypeAxis ? "by-file-type-list" : "by-type-list"}
                data-axis={usesFileTypeAxis ? "file-type" : "legal"}
              >
                {rows.map((row) => {
                  const pct = row.total > 0 ? (row.available / row.total) * 100 : 0

                  return (
                    <div
                      key={row.key}
                      className="text-xs p-2 rounded bg-muted/50"
                      data-testid={`type-row-${row.key}`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-muted-foreground capitalize">
                          {row.label}
                        </span>
                        <span className={cn("font-medium shrink-0", getCoverageColor(pct))}>
                          {row.available}/{row.total}
                        </span>
                      </div>
                      {row.legalCategories.length > 0 && (
                        <p
                          className="mt-1 text-[11px] text-muted-foreground/80"
                          data-testid={`legal-categories-${row.key}`}
                        >
                          <span className="text-muted-foreground/60">legal: </span>
                          {row.legalCategories
                            .map((c) => `${c.label} (${c.count})`)
                            .join(" · ")}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export function TransparencyMap() {
  const { data, isLoading, error } = useTransparencyOverview()

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            Mapa de Transparencia del Estado
          </CardTitle>
          <CardDescription className="flex items-center gap-1.5 text-red-600">
            <AlertTriangle className="h-4 w-4" />
            No se pudo cargar el inventario de documentos (GET /compliance/documents/overview).
            Verificá que el backend esté activo.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64 mt-2" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!data || !data.jurisdictions || data.jurisdictions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5" />
            Mapa de Transparencia
          </CardTitle>
          <CardDescription>
            No hay datos de transparencia cargados. Ejecuta la inicialización del inventario de documentos.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  // Sort jurisdictions: nacion first, then provincia, then municipio
  const levelOrder = { nacion: 0, provincia: 1, municipio: 2 }
  const sortedJurisdictions = [...data.jurisdictions].sort((a, b) => {
    const aLevel = levelOrder[getJurisdictionLevel(a)] ?? 3
    const bLevel = levelOrder[getJurisdictionLevel(b)] ?? 3
    return aLevel - bLevel
  })

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" />
              Mapa de Transparencia del Estado
            </CardTitle>
            <CardDescription className="mt-1">
              Disponibilidad de documentos requeridos por Ley de Transparencia por jurisdicción
            </CardDescription>
          </div>
          <div className="text-right">
            <div className={cn("text-2xl font-bold", getCoverageColor(data.overall_coverage))}>
              {data.overall_coverage.toFixed(0)}%
            </div>
            <p className="text-xs text-muted-foreground" data-testid="overall-coverage">
              Cobertura global ({data.total_processed}/{data.total_documents})
            </p>
          </div>
        </div>
        {data.total_documents === 0 && (
          <p className="text-xs text-muted-foreground mt-2" data-testid="inventory-empty">
            El inventario de documentos requeridos está vacío. Ejecutá la sincronización
            (POST /api/v1/compliance/documents/sync) para cargarlo desde required_documents.json.
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {sortedJurisdictions.map((jurisdiction) => (
          <JurisdictionCard
            key={jurisdiction.jurisdiction_key ?? jurisdiction.jurisdiction_code}
            jurisdiction={jurisdiction}
            taxonomy={data.file_type_taxonomy}
          />
        ))}
      </CardContent>
    </Card>
  )
}
