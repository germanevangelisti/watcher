import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { FileText, Calendar, Building2 } from "lucide-react"
import dayjs from "dayjs"
import { cn } from "@/lib/utils"
import type { Boletin } from "@/types"

interface BoletinCardProps {
  boletin: Boletin
  onView?: (id: number) => void
  className?: string
}

export function BoletinCard({ boletin, onView, className }: BoletinCardProps) {
  const getStatusColor = (processed: boolean) => {
    return processed
      ? "bg-green-500/10 text-green-400 border-green-500/20"
      : "bg-yellow-500/10 text-yellow-400 border-yellow-500/20"
  }

  return (
    <Card
      className={cn(
        "hover:bg-surface-elevated transition-colors cursor-pointer",
        className
      )}
      onClick={() => onView?.(boletin.id)}
    >
      <CardContent className="p-6">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 flex-1">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <FileText className="h-5 w-5 text-blue-400" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold truncate">{boletin.filename}</h3>
                <p className="text-sm text-muted-foreground">
                  {boletin.seccion_nombre || boletin.section}
                </p>
              </div>
            </div>
            <Badge className={getStatusColor(boletin.processed)}>
              {boletin.processed ? "Procesado" : "Pendiente"}
            </Badge>
          </div>

          {/* Info */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>{dayjs(boletin.date).format("DD/MM/YYYY")}</span>
            </div>
            {boletin.jurisdiccion_nombre && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Building2 className="h-4 w-4" />
                <span className="truncate">{boletin.jurisdiccion_nombre}</span>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between pt-2 border-t">
            <span className="text-xs text-muted-foreground">
              {boletin.fuente || "Fuente no especificada"}
            </span>
            <Button variant="ghost" size="sm" onClick={(e) => {
              e.stopPropagation()
              onView?.(boletin.id)
            }}>
              Ver detalle →
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
