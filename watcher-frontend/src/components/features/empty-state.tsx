import { AlertCircle, XCircle } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <Card>
      <CardContent className="p-12 text-center">
        <div className="flex flex-col items-center gap-4">
          {icon || <AlertCircle className="h-12 w-12 text-muted-foreground" />}
          <div className="space-y-2">
            <h3 className="text-lg font-semibold">{title}</h3>
            {description && (
              <p className="text-sm text-muted-foreground max-w-md">{description}</p>
            )}
          </div>
          {action && (
            <Button onClick={action.onClick} className="mt-2">
              {action.label}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
}

export function ErrorState({ 
  title = "Error", 
  message, 
  onRetry 
}: ErrorStateProps) {
  return (
    <Card className="border-red-500/20">
      <CardContent className="p-12 text-center">
        <div className="flex flex-col items-center gap-4">
          <XCircle className="h-12 w-12 text-red-400" />
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-red-400">{title}</h3>
            <p className="text-sm text-muted-foreground max-w-md">{message}</p>
          </div>
          {onRetry && (
            <Button onClick={onRetry} variant="outline" className="mt-2">
              Reintentar
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
