/**
 * SyncPanel - Shows sync configuration per jurisdiction and allows triggering sync.
 */

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useSyncConfigs, useTriggerJurisdictionSync } from "@/lib/api/hooks/use-sync"
import { useJurisdicciones } from "@/lib/api/hooks/use-jurisdicciones"
import { RefreshCw, Loader2, ChevronDown, ChevronRight, CheckCircle2, AlertCircle, Clock } from "lucide-react"
import { useState } from "react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

function SyncStatusBadge({ status }: { status: string }) {
  switch (status) {
    case "completed":
      return (
        <Badge variant="outline" className="gap-1 text-green-500 border-green-500/20 text-xs">
          <CheckCircle2 className="h-3 w-3" />
          Completado
        </Badge>
      )
    case "syncing":
      return (
        <Badge variant="outline" className="gap-1 text-blue-500 border-blue-500/20 text-xs">
          <Loader2 className="h-3 w-3 animate-spin" />
          Sincronizando
        </Badge>
      )
    case "failed":
      return (
        <Badge variant="outline" className="gap-1 text-red-500 border-red-500/20 text-xs">
          <AlertCircle className="h-3 w-3" />
          Fallido
        </Badge>
      )
    default:
      return (
        <Badge variant="outline" className="gap-1 text-muted-foreground text-xs">
          <Clock className="h-3 w-3" />
          Sin sync
        </Badge>
      )
  }
}

export function SyncPanel() {
  const [expanded, setExpanded] = useState(false)
  const { data: configs, isLoading: configsLoading } = useSyncConfigs()
  const { data: jurisdicciones } = useJurisdicciones()
  const triggerSync = useTriggerJurisdictionSync()

  const handleTriggerSync = (jurisdiccionId: number, nombre: string) => {
    triggerSync.mutate(
      { jurisdiccionId },
      {
        onSuccess: () => {
          toast.success(`Sincronización iniciada para ${nombre}`)
        },
        onError: (error: Error) => {
          toast.error(`Error al iniciar sync: ${error.message}`)
        },
      }
    )
  }

  // Combine jurisdictions with their configs
  const jurisdictionList = (jurisdicciones || []).map((j) => {
    const config = configs?.find((c) => c.jurisdiccion_id === j.id)
    return { ...j, config }
  })

  const enabledCount = configs?.filter((c) => c.sync_enabled).length ?? 0

  return (
    <Card>
      <CardHeader
        className="cursor-pointer pb-3"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <RefreshCw className="h-4 w-4" />
            Sincronización por Jurisdicción
            {enabledCount > 0 && (
              <Badge variant="secondary" className="text-xs">
                {enabledCount} activas
              </Badge>
            )}
          </CardTitle>
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-0">
          {configsLoading ? (
            <p className="text-sm text-muted-foreground">Cargando configuraciones...</p>
          ) : jurisdictionList.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No hay jurisdicciones configuradas. Configura la sincronización desde el backend.
            </p>
          ) : (
            <div className="space-y-2">
              {jurisdictionList.slice(0, 10).map((j) => (
                <div
                  key={j.id}
                  className={cn(
                    "flex items-center justify-between p-2.5 rounded-lg border",
                    j.config?.sync_enabled
                      ? "border-green-500/20 bg-green-500/5"
                      : "border-border/50"
                  )}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div>
                      <p className="text-sm font-medium truncate">{j.nombre}</p>
                      <p className="text-xs text-muted-foreground capitalize">{j.tipo}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {j.config && <SyncStatusBadge status={j.config.last_sync_status} />}
                    {j.config?.last_sync_date && (
                      <span className="text-[10px] text-muted-foreground hidden sm:block">
                        {j.config.last_sync_date}
                      </span>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1 h-7 text-xs"
                      disabled={!j.config?.sync_enabled || triggerSync.isPending}
                      onClick={() => handleTriggerSync(j.id, j.nombre)}
                    >
                      {triggerSync.isPending ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3 w-3" />
                      )}
                      Sync
                    </Button>
                  </div>
                </div>
              ))}
              {jurisdictionList.length > 10 && (
                <p className="text-xs text-muted-foreground text-center">
                  +{jurisdictionList.length - 10} jurisdicciones más
                </p>
              )}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}
