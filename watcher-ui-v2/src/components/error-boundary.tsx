import { Component } from "react"
import type { ErrorInfo, ReactNode } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertTriangle } from "lucide-react"

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo)
    this.props.onError?.(error, errorInfo)
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: undefined })
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen flex items-center justify-center p-6">
          <Card className="max-w-lg w-full border-red-500/20">
            <CardContent className="p-12 text-center">
              <div className="flex flex-col items-center gap-6">
                <div className="p-4 rounded-full bg-red-500/10">
                  <AlertTriangle className="h-12 w-12 text-red-400" />
                </div>
                <div className="space-y-2">
                  <h2 className="text-2xl font-bold text-red-400">
                    Algo salió mal
                  </h2>
                  <p className="text-muted-foreground">
                    La aplicación encontró un error inesperado
                  </p>
                  {this.state.error && (
                    <details className="mt-4 text-left">
                      <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
                        Ver detalles técnicos
                      </summary>
                      <pre className="mt-2 p-4 bg-surface-elevated rounded-md text-xs overflow-auto">
                        {this.state.error.message}
                        {"\n\n"}
                        {this.state.error.stack}
                      </pre>
                    </details>
                  )}
                </div>
                <div className="flex gap-4">
                  <Button onClick={this.handleReset} variant="outline">
                    Intentar de nuevo
                  </Button>
                  <Button onClick={() => window.location.href = "/"}>
                    Ir al inicio
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}
