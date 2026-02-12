import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { FileText, TrendingUp } from "lucide-react"
import { cn } from "@/lib/utils"

interface SearchResultCardProps {
  document: string
  metadata: {
    filename: string
    date: string
    section: string
    document_id: string
  }
  score: number
  distance?: number
  onViewDocument?: (filename: string) => void
  className?: string
}

export function SearchResultCard({
  document,
  metadata,
  score,
  distance,
  onViewDocument,
  className,
}: SearchResultCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "text-green-400"
    if (score >= 0.6) return "text-yellow-400"
    return "text-orange-400"
  }

  return (
    <Card className={cn("hover:bg-surface-elevated transition-colors", className)}>
      <CardContent className="p-6">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 flex-1">
              <div className="p-2 rounded-lg bg-purple-500/10">
                <FileText className="h-5 w-5 text-purple-400" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold truncate">{metadata.filename}</h3>
                <p className="text-sm text-muted-foreground">
                  {metadata.section} • {metadata.date}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <TrendingUp className={cn("h-4 w-4", getScoreColor(score))} />
              <Badge variant="outline" className={cn("font-mono", getScoreColor(score))}>
                {(score * 100).toFixed(1)}%
              </Badge>
            </div>
          </div>

          {/* Content Preview */}
          <p className="text-sm leading-relaxed line-clamp-3 text-muted-foreground">
            {document}
          </p>

          {/* Footer */}
          <div className="flex items-center justify-between pt-2 border-t">
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span>ID: {metadata.document_id}</span>
              {distance !== undefined && (
                <span>Distancia: {distance.toFixed(4)}</span>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onViewDocument?.(metadata.filename)}
            >
              Ver documento →
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
