import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { FileText, Calendar, CheckCircle2, Clock } from "lucide-react"
import { Link } from "@tanstack/react-router"
import type { Boletin } from "@/types"
import dayjs from "dayjs"

interface BoletinCardProps {
  boletin: Boletin
}

export function BoletinCard({ boletin }: BoletinCardProps) {
  const formattedDate = dayjs(boletin.date).format("DD/MM/YYYY")

  return (
    <Card className="hover:border-primary/50 transition-colors">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1 flex-1">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              {boletin.filename}
            </CardTitle>
            <CardDescription className="flex items-center gap-2 text-sm">
              <Calendar className="h-3 w-3" />
              {formattedDate} • Sección {boletin.section}
            </CardDescription>
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
      </CardHeader>
      
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="grid grid-cols-3 gap-4 text-sm flex-1">
            <div>
              <p className="text-muted-foreground text-xs">Año</p>
              <p className="font-medium">{boletin.year}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">Mes</p>
              <p className="font-medium">{boletin.month}</p>
            </div>
            {boletin.total_pages && (
              <div>
                <p className="text-muted-foreground text-xs">Páginas</p>
                <p className="font-medium">{boletin.total_pages}</p>
              </div>
            )}
          </div>
          
          <Link to="/documentos/$id" params={{ id: boletin.id.toString() }}>
            <Button variant="outline" size="sm">
              Ver detalle
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}
