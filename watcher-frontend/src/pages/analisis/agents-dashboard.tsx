import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { FadeTransition } from "@/components/ui/fade-transition"
import { ChatMarkdown } from "@/components/features/chat-markdown"
import { LlmProviderCard } from "@/components/features/llm-provider-card"
import { chatSources } from "@/lib/chat-sources"
import {
  llmCredit,
  readStoredSelection,
  storeSelection,
  type ChatLlmSelection,
} from "@/lib/llm-providers"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAgentHealth, useAgentChat, useAgentChatClear, useLlmProviders, useSystemStatistics, useTopRiskDocuments, useTransparencyTrends } from "@/lib/api"
import type { ChatLlm } from "@/lib/api"
import { Bot, Activity, MessageSquare, Send, TrendingUp, AlertTriangle, BarChart3, RefreshCw, CheckCircle2, XCircle, Trash2 } from "lucide-react"

/**
 * Fuentes de un turno del asistente. Se declaran desde las claves que el backend
 * consultó de verdad (`data_used`); si el turno no trae ninguna, no se inventa una
 * cita: se dice que no hay fuentes estructuradas. En un producto de transparencia
 * una respuesta sin respaldo tiene que poder distinguirse de una con respaldo.
 */
function ChatSources({ dataUsed }: { dataUsed?: string[] }) {
  const sources = chatSources(dataUsed)

  if (sources.length === 0) {
    return (
      <p className="mt-2 text-[11px] text-muted-foreground" data-testid="chat-sources-empty">
        Sin fuentes estructuradas
      </p>
    )
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5" data-testid="chat-sources">
      <span className="text-[11px] text-muted-foreground">Fuentes:</span>
      {sources.map((source) => (
        <Badge
          key={source.key}
          variant="outline"
          className="text-[10px] font-normal"
          data-testid={`chat-source-${source.key}`}
        >
          {source.label}
        </Badge>
      ))}
    </div>
  )
}

// Empty state del chat: preguntas ejecutivas de presupuesto (copy literal acordado con PO)
const CHAT_SUGGESTIONS = [
  "¿Qué porcentaje del presupuesto vigente se ha ejecutado?",
  "¿Qué organismos concentran mayor gasto?",
  "¿Qué finalidades presentan mayor desvío?",
] as const

/**
 * El motivo que devolvió el backend, si lo hay.
 *
 * El 400 del proveedor elegido trae la causa exacta ("falta ANTHROPIC_API_KEY",
 * "el modelo «x» no está descargado"). Un "no se pudo obtener respuesta" encima
 * de eso borraría la única información que el usuario necesita para arreglarlo.
 */
function extraerDetalleDeError(error: unknown): string | null {
  if (typeof error !== "object" || error === null) return null

  const dato = (error as { response?: { data?: unknown } }).response?.data
  if (typeof dato === "string") return dato.trim() || null
  if (typeof dato !== "object" || dato === null) return null

  const detalle = (dato as { detail?: unknown }).detail
  return typeof detalle === "string" && detalle.trim() ? detalle : null
}

export function AgentsDashboard() {
  const [chatMessage, setChatMessage] = useState("")
  const [chatHistory, setChatHistory] = useState<
    Array<{ role: string; content: string; dataUsed?: string[]; llm?: ChatLlm | null; isError?: boolean }>
  >([])
  // Se inicializa leyendo lo recordado por el navegador: la elección sobrevive a
  // recargar la página, que es lo que hace usable comparar entre sesiones.
  const [llmSelection, setLlmSelection] = useState<ChatLlmSelection | null>(() =>
    readStoredSelection(),
  )

  const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useAgentHealth()
  const { data: stats, isLoading: statsLoading } = useSystemStatistics()
  const { data: topRisk, isLoading: riskLoading } = useTopRiskDocuments(5)
  const { isLoading: trendsLoading } = useTransparencyTrends()
  const { data: llmCatalog, isLoading: llmLoading, isError: llmError } = useLlmProviders()

  const chatMutation = useAgentChat()
  const clearMutation = useAgentChatClear()
  const [clearFailed, setClearFailed] = useState(false)

  const handleLlmChange = (selection: ChatLlmSelection) => {
    setLlmSelection(selection)
    storeSelection(selection)
  }

  /**
   * Lo que se muestra en el selector y lo que viaja en el turno salen de acá.
   *
   * Sin elección explícita se usa el proveedor que el entorno está usando —el que
   * la tarjeta ya muestra como valor inicial—, y se manda nombrado. Dejar que el
   * backend decida mientras la pantalla afirma un proveedor permitiría que un
   * cambio en el `.env` cambie quién responde sin que la pantalla se entere: es
   * exactamente el default invisible que esta tarjeta vino a destapar.
   */
  const llmEffective: ChatLlmSelection | null =
    llmSelection ??
    (llmCatalog?.configured
      ? {
          provider: llmCatalog.configured.provider,
          ...(llmCatalog.configured.model ? { model: llmCatalog.configured.model } : {}),
        }
      : null)

  const sendMessage = async (text: string) => {
    if (!text.trim() || chatMutation.isPending) return

    const userMessage = { role: "user", content: text }
    setChatHistory((prev) => [...prev, userMessage])
    setChatMessage("")

    try {
      const response = await chatMutation.mutateAsync({
        query: text,
        provider: llmEffective?.provider,
        model: llmEffective?.model,
      })
      const content = typeof response === 'string' ? response : (response.response || JSON.stringify(response))
      // `data_used` se guarda con el mensaje: es lo que permite citar la fuente
      // que el agente consultó, y se pierde si sólo se guarda el texto.
      const dataUsed = typeof response === 'string' ? undefined : response.data_used
      // El proveedor se guarda **por burbuja** y no se lee del selector al
      // renderizar: se puede cambiar de proveedor entre mensajes, y una burbuja
      // vieja tiene que seguir diciendo quién la escribió.
      const llm = typeof response === 'string' ? undefined : response.llm
      const assistantMessage = { role: "assistant", content, dataUsed, llm }
      setChatHistory((prev) => [...prev, assistantMessage])
    } catch (error) {
      // El 400 del backend dice qué le falta al proveedor elegido: pisarlo con un
      // "no se pudo" genérico borraría justamente lo que el usuario necesita para
      // arreglarlo (una key, un paquete, un modelo sin descargar).
      const detalle = extraerDetalleDeError(error)
      const errorMessage = {
        role: "assistant",
        content: detalle
          ? `Error: ${detalle}`
          : "Error: No se pudo obtener respuesta del agente",
        isError: true,
      }
      setChatHistory((prev) => [...prev, errorMessage])
    }
  }

  const handleSendMessage = () => sendMessage(chatMessage)

  // "Limpiar chat": vacía la conversación en pantalla y el historial del
  // servidor. La UI se limpia siempre y el fallo del server se declara: mostrar
  // un chat vacío sobre un agente que todavía recuerda los turnos es peor que un
  // error visible. Si el borrado falló, el botón queda habilitado para reintentar.
  const handleClearChat = () => {
    setChatHistory([])
    setChatMessage("")
    setClearFailed(false)
    clearMutation.mutateAsync().catch(() => setClearFailed(true))
  }

  const canClear =
    (chatHistory.length > 0 || clearFailed) && !chatMutation.isPending && !clearMutation.isPending

  // Chip: rellena el input con el texto y dispara el mismo envío que "Enviar"
  const handleSuggestion = (text: string) => {
    setChatMessage(text)
    void sendMessage(text)
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
              <div className="flex items-start justify-between gap-2">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5" />
                    Chat con Insight Agent
                  </CardTitle>
                  <CardDescription>
                    Realiza consultas sobre el sistema y obtén insights
                  </CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-2 shrink-0"
                  onClick={handleClearChat}
                  disabled={!canClear}
                  data-testid="chat-clear"
                >
                  <Trash2 className="h-4 w-4" />
                  Limpiar chat
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {clearFailed && (
                <p className="text-xs text-red-600" role="status" data-testid="chat-clear-error">
                  Se limpió el chat en pantalla, pero el servidor no confirmó el borrado: el
                  agente puede seguir recordando los turnos anteriores. Reintentá "Limpiar chat".
                </p>
              )}

              {/* Configuración del proveedor: va arriba de la conversación
                  porque es lo que decide quién va a redactar lo que sigue. */}
              <LlmProviderCard
                catalog={llmCatalog}
                isLoading={llmLoading}
                isError={llmError}
                selection={llmEffective}
                onChange={handleLlmChange}
              />

              {/* Chat History */}
              <div className="border rounded-lg p-4 h-96 overflow-y-auto space-y-4">
                {chatHistory.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    <div className="text-center">
                      <Bot className="h-12 w-12 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No hay mensajes aún</p>
                      <p className="text-xs mt-1">Envía un mensaje o elegí una pregunta para comenzar</p>
                      <div className="mt-4 flex flex-wrap justify-center gap-2" data-testid="chat-suggestions">
                        {CHAT_SUGGESTIONS.map((text) => (
                          <Button
                            key={text}
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-auto whitespace-normal text-left text-xs"
                            onClick={() => handleSuggestion(text)}
                            disabled={chatMutation.isPending}
                          >
                            {text}
                          </Button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  chatHistory.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        data-role={msg.role}
                        className={`max-w-[80%] rounded-lg p-3 ${
                          msg.role === "user"
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted"
                        }`}
                      >
                        {/* El agente contesta en Markdown: se renderiza. Lo que
                            escribe el usuario va plano, tal como lo tipeó. */}
                        {msg.role === "user" ? (
                          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                        ) : (
                          <>
                            <ChatMarkdown content={msg.content} />
                            {/* Con qué se redactó: es el dato que permite
                                comparar dos respuestas a la misma pregunta, y
                                sin él la comparación es de memoria. */}
                            {!msg.isError && llmCredit(msg.llm, llmCatalog?.providers) && (
                              <p
                                className="mt-2 text-[11px] text-muted-foreground"
                                data-testid="chat-llm-credit"
                              >
                                {llmCredit(msg.llm, llmCatalog?.providers)}
                              </p>
                            )}
                            {/* Una burbuja de error no lleva fuentes: no hubo consulta. */}
                            {!msg.isError && <ChatSources dataUsed={msg.dataUsed} />}
                          </>
                        )}
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
                  {topRisk.map((doc: Record<string, unknown>, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex-1">
                        <p className="text-sm font-medium">{(doc.title as string) || `Documento ${doc.id}`}</p>
                        <p className="text-xs text-muted-foreground">{doc.date as string}</p>
                      </div>
                      <Badge variant="destructive">{(doc.risk_score as string) || "Alto"}</Badge>
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
