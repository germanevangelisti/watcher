import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface EntityBadgeProps {
  type: string
  className?: string
}

const entityColors: Record<string, string> = {
  PERSONA: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  ORGANIZACION: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  LUGAR: "bg-green-500/10 text-green-400 border-green-500/20",
  MONTO: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  FECHA: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  LEGAL: "bg-red-500/10 text-red-400 border-red-500/20",
}

export function EntityBadge({ type, className }: EntityBadgeProps) {
  const colorClass = entityColors[type] || "bg-gray-500/10 text-gray-400 border-gray-500/20"

  return (
    <Badge className={cn(colorClass, className)}>
      {type}
    </Badge>
  )
}
