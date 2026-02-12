import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { FadeTransition } from "@/components/ui/fade-transition"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAgentHealth, useAgentChat, useSystemStatistics, useTopRiskDocuments, useTransparencyTrends } from "@/lib/api"
import { Bot, Activity, MessageSquare, Send, TrendingUp, AlertTriangle, BarChart3, RefreshCw, CheckCircle2, XCircle } from "lucide-react"

export function AgentsDashboard() {
  const [chatMessage, setChatMessage] = useState("")
  const [chatHistory, setChatHistory] = useState<Array<{ role: string; content: string }>>([])

  const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useAgentHealth()
  const { data: stats, isLoading: statsLoading } = useSystemStatistics()
  const { data: topRisk, isLoading: riskLoading } = useTopRiskDocuments(5)
  const { isLoading: trendsLoading } = useTransparencyTrends()
  
  const chatMutation = useAgentChat()

  const handleSendMessage = async () => {
    if (!chatMessage.trim()) return

    const userMessage = { role: "user", content: chatMessage }
    setChatHistory((prev) => [...prev, userMessage])
    setChatMessage("")

    try {
      const response = await chatMutation.mutateAsync(chatMessage)
      const content = typeof response === 'string' ? response : (response.response || JSON.stringify(response))
      const assistantMessage = { role: "assistant", content }
      setChatHistory((prev) => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage = { role: "assistant", content: "Error: No se pudo obtener respuesta del agente" }
      setChatHistory((prev) => [...prev, errorMessage])
    }
  }

  const getAgentIcon = () => {
    return <Bot className="h-4 w-4" />
  }

  const getAgentName = (agentType: string) => {
    const names: Record<string, string> = {
      document_intelligence: "Document Intelligence",
      anomaly_detection: "Anomaly Detection",
      insight_reporting: "Insight Reporting",
      historical_intelligence: "Historical Intelligence",
    }
    return names[agentType] || agentType
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "text-green-500"
      case "idle":
        return "text-yellow-500"
      case "error":
        return "text-red-500"
      default:
        return "text-gray-500"
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Panel de Agentes</h1>
          <p className="text-muted-foreground mt-2">
            Monitoreo y control de agentes de IA
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetchHealth()}
          disabled={healthLoading}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${healthLoading ? "animate-spin" : ""}`} />
          Actualizar
        </Button>
      </div>

      <Tabs defaultValue="agents" className="space-y-4">
        <TabsList>
          <TabsTrigger value="agents">Agentes</TabsTrigger>
          <TabsTrigger value="chat">Chat con Insights</TabsTrigger>
          <TabsTrigger value="metrics">Métricas</TabsTrigger>
        </TabsList>

        <TabsContent value="agents" className="space-y-4">
          {/* System Status */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5" />
                    Estado del Sistema
                  </CardTitle>
                  <CardDescription>
                    {health?.active_workflows || 0} workflows activos • {health?.total_tasks_completed || 0} tareas completadas
                  </CardDescription>
                </div>
                {health && (
                  <Badge variant={health.system_status === "healthy" ? "default" : "secondary"}>
                    {health.system_status}
                  </Badge>
                )}
              </div>
            </CardHeader>
          </Card>

          {/* Agents Grid */}
          <FadeTransition
            isLoading={healthLoading}
            skeleton={
              <div className="grid gap-4 md:grid-cols-2">
                {[1, 2, 3, 4].map((i) => (
                  <Card key={i}>
                    <CardHeader>
                      <Skeleton className="h-5 w-32" />
                      <Skeleton className="h-4 w-24 mt-2" />
                    </CardHeader>
                    <CardContent>
                      <Skeleton className="h-4 w-full" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            }
          >
            {health && (
              <div className="grid gap-4 md:grid-cols-2">
                {health.agents.map((agent) => (
                  <Card key={agent.agent_type}>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div>
                          <CardTitle className="text-lg flex items-center gap-2">
                            {getAgentIcon()}
                            {getAgentName(agent.agent_type)}
                          </CardTitle>
                          <CardDescription className="mt-1">
                            {agent.tasks_processed} tareas procesadas
                          </CardDescription>
                        </div>
                        <div className="flex flex-col items-end gap-2">
                          <Badge variant={agent.is_available ? "default" : "secondary"}>
                            {agent.is_available ? (
                              <CheckCircle2 className="h-3 w-3 mr-1" />
                            ) : (
                              <XCircle className="h-3 w-3 mr-1" />
                            )}
                            {agent.is_available ? "Disponible" : "No disponible"}
                          </Badge>
                          <span className={`text-sm font-medium ${getStatusColor(agent.status)}`}>
                            {agent.status}
                          </span>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="text-sm text-muted-foreground">
                        Tipo: {agent.agent_type.replace("_", " ")}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </FadeTransition>
        </TabsContent>

        <TabsContent value="chat" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Chat con Insight Agent
              </CardTitle>
              <CardDescription>
                Realiza consultas sobre el sistema y obtén insights
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Chat History */}
              <div className="border rounded-lg p-4 h-96 overflow-y-auto space-y-4">
                {chatHistory.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <div className="text-center">
                      <Bot className="h-12 w-12 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No hay mensajes aún</p>
                      <p className="text-xs mt-1">Envía un mensaje para comenzar</p>
                    </div>
                  </div>
                ) : (
                  chatHistory.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-lg p-3 ${
                          msg.role === "user"
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted"
                        }`}
                      >
                        <p className="text-sm">{msg.content}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Chat Input */}
              <div className="flex gap-2">
                <Input
                  placeholder="Escribe tu consulta..."
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault()
                      handleSendMessage()
                    }
                  }}
                  disabled={chatMutation.isPending}
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={!chatMessage.trim() || chatMutation.isPending}
                  className="gap-2"
                >
                  <Send className="h-4 w-4" />
                  Enviar
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="metrics" className="space-y-4">
          {/* Quick Insights */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Sistema
                </CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {statsLoading ? (
                  <Skeleton className="h-10 w-24" />
                ) : (
                  <>
                    <div className="text-3xl font-bold">{stats?.total_documents || 0}</div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Documentos procesados
                    </p>
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Riesgo
                </CardTitle>
                <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {riskLoading ? (
                  <Skeleton className="h-10 w-24" />
                ) : (
                  <>
                    <div className="text-3xl font-bold">{topRisk?.length || 0}</div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Documentos de alto riesgo
                    </p>
                  </>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Tendencias
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {trendsLoading ? (
                  <Skeleton className="h-10 w-24" />
                ) : (
                  <>
                    <div className="text-3xl font-bold">-</div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Análisis de transparencia
                    </p>
                  </>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Top Risk Documents */}
          {topRisk && topRisk.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Documentos de Alto Riesgo</CardTitle>
                <CardDescription>
                  Top 5 documentos que requieren atención
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {topRisk.map((doc: any, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium">{doc.title || `Documento ${doc.id}`}</p>
                        <p className="text-xs text-muted-foreground">{doc.date}</p>
                      </div>
                      <Badge variant="destructive">{doc.risk_score || "Alto"}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
