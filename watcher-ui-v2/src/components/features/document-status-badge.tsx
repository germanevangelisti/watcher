/**
 * DocumentStatusBadge - Shows document pipeline status with color-coded badge.
 * Pulsating animation for in-progress stages.
 */

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface DocumentStatusBadgeProps {
  status: string
  className?: string
}

const STATUS_CONFIG: Record<string, { label: string; classes: string; pulse: boolean }> = {
  pending: {
    label: "Pendiente",
    classes: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
    pulse: false,
  },
  extracting: {
    label: "Extrayendo",
    classes: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    pulse: true,
  },
  cleaning: {
    label: "Limpiando",
    classes: "bg-sky-500/10 text-sky-400 border-sky-500/20",
    pulse: true,
  },
  chunking: {
    label: "Chunking",
    classes: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    pulse: true,
  },
  indexing: {
    label: "Indexando",
    classes: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    pulse: true,
  },
  completed: {
    label: "Completado",
    classes: "bg-green-500/10 text-green-400 border-green-500/20",
    pulse: false,
  },
  failed: {
    label: "Error",
    classes: "bg-red-500/10 text-red-400 border-red-500/20",
    pulse: false,
  },
}

export function DocumentStatusBadge({ status, className }: DocumentStatusBadgeProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending

  return (
    <Badge
      className={cn(
        config.classes,
        config.pulse && "animate-pulse",
        className
      )}
    >
      {config.pulse && (
        <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-current inline-block" />
      )}
      {config.label}
    </Badge>
  )
}
