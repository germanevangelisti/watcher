import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { useTransparencyOverview } from "@/lib/api/hooks/use-transparency"
import type { JurisdictionSummary } from "@/lib/api/hooks/use-transparency"
import { MapPin, Building2, Landmark, FileCheck, FileX, FileDown, ChevronDown, ChevronRight, Scale } from "lucide-react"
import { useState } from "react"
import { cn } from "@/lib/utils"

function getJurisdictionIcon(code: string) {
  switch (code) {
    case "AR":
      return <Landmark className="h-5 w-5" />
    case "CBA":
      return <Building2 className="h-5 w-5" />
    default:
      return <MapPin className="h-5 w-5" />
  }
}

function getJurisdictionLevel(code: string): "nacion" | "provincia" | "municipio" {
  if (code === "AR") return "nacion"
  if (code === "CBA") return "provincia"
  return "municipio"
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

function JurisdictionCard({ jurisdiction }: { jurisdiction: JurisdictionSummary }) {
  const [expanded, setExpanded] = useState(false)
  const level = getJurisdictionLevel(jurisdiction.jurisdiction_code)

  return (
    <div
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
            {getJurisdictionIcon(jurisdiction.jurisdiction_code)}
          </div>
          <div>
            <h4 className="font-semibold text-sm">{jurisdiction.jurisdiction_name}</h4>
            <p className="text-xs text-muted-foreground capitalize">{level}</p>
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
          {jurisdiction.applicable_laws.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1.5">Leyes aplicables:</p>
              <div className="flex flex-wrap gap-1.5">
                {jurisdiction.applicable_laws.map((law, i) => (
                  <Badge key={i} variant="secondary" className="text-xs font-normal">
                    <Scale className="h-3 w-3 mr-1" />
                    {law}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Documents by type */}
          {Object.keys(jurisdiction.by_type).length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1.5">Documentos por tipo:</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {Object.entries(jurisdiction.by_type).map(([docType, counts]) => {
                  const total = (counts.missing || 0) + (counts.downloaded || 0) + (counts.processed || 0)
                  const available = (counts.downloaded || 0) + (counts.processed || 0)
                  const pct = total > 0 ? (available / total) * 100 : 0

                  return (
                    <div key={docType} className="flex items-center justify-between text-xs p-2 rounded bg-muted/50">
                      <span className="text-muted-foreground capitalize">
                        {docType.replace(/_/g, " ")}
                      </span>
                      <span className={cn("font-medium", getCoverageColor(pct))}>
                        {available}/{total}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function TransparencyMap() {
  const { data, isLoading, error } = useTransparencyOverview()

  if (error) {
    return null // Silently fail if compliance data is not available yet
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

  if (!data || data.jurisdictions.length === 0) {
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
    const aLevel = levelOrder[getJurisdictionLevel(a.jurisdiction_code)] ?? 3
    const bLevel = levelOrder[getJurisdictionLevel(b.jurisdiction_code)] ?? 3
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
            <p className="text-xs text-muted-foreground">
              Cobertura global ({data.total_processed}/{data.total_documents})
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {sortedJurisdictions.map((jurisdiction) => (
          <JurisdictionCard
            key={jurisdiction.jurisdiction_code}
            jurisdiction={jurisdiction}
          />
        ))}
      </CardContent>
    </Card>
  )
}
