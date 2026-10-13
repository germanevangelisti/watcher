import { useQuery, useMutation } from "@tanstack/react-query"
import apiClient from "../client"

interface Agent {
  agent_type: string
  status: string
  is_available: boolean
  tasks_processed: number
}

interface AgentHealth {
  system_status: string
  agents: Agent[]
  active_workflows: number
  total_tasks_completed: number
}

export function useAgentHealth() {
  return useQuery({
    queryKey: ["agent-health"],
    queryFn: async () => {
      const { data } = await apiClient.get<AgentHealth>("/agents/health")
      return data
    },
    refetchInterval: 10000, // Refetch every 10 seconds
  })
}

/**
 * Quién redactó una respuesta del chat.
 *
 * El backend lo devuelve por turno y no por configuración, a propósito: el
 * proveedor se puede elegir en cada mensaje, así que una burbuja vieja puede
 * haberla escrito otro modelo. `null` significa que **no la escribió un
 * modelo** —el texto de cortesía que el agente responde solo, o el de fallback
 * cuando el modelo no contestó—, y la burbuja lo dice así en vez de atribuirle
 * la frase a un proveedor que no la redactó.
 */
export interface ChatLlm {
  provider: string | null
  model: string | null
}

interface ChatResponse {
  response: string
  /**
   * Claves de las fuentes que el agente consultó para armar la respuesta
   * (`query_with_data` devuelve `list(data_context.keys())`). Son claves
   * estructuradas, no citas redactadas: se muestran traducidas con
   * `chatSources()` de `@/lib/chat-sources`.
   *
   * Opcional a propósito: un backend anterior a esta historia no lo manda y la
   * burbuja tiene que seguir renderizando el texto.
   */
  data_used?: string[]
  agent?: string
  llm?: ChatLlm | null
  timestamp?: string
}

export interface ChatTurn {
  query: string
  /** Proveedor elegido en la tarjeta. Sin esto el backend usa el del entorno. */
  provider?: string
  model?: string
}

export function useAgentChat() {
  return useMutation({
    // Acepta el string de siempre además del turno completo: el contrato viejo
    // (`useAgentChat().mutate("...")`) sigue funcionando y no obliga a tocar
    // los llamadores que no eligen proveedor.
    mutationFn: async (turno: string | ChatTurn) => {
      const body = typeof turno === "string" ? { query: turno } : turno
      const { data } = await apiClient.post<ChatResponse>("/agents/chat", body)
      return data
    },
  })
}

/** Un proveedor de LLM tal como lo publica el backend, con su disponibilidad. */
export interface LlmProviderOption {
  id: string
  label: string
  /** `true` = nada sale de la máquina. */
  local: boolean
  available: boolean
  /** Por qué **no** se puede usar, o la advertencia si es remoto. */
  reason: string | null
  model: string | null
  /** Modelos ya descargados (`ollama`); vacío en los que no se eligen. */
  models: string[]
}

/** Con qué proveedor arranca el chat cuando nadie elige, y de dónde sale. */
export interface ConfiguredLlm {
  provider: string
  model: string | null
  requested: string
  origin: string
  /** Lo configurado no se pudo construir y el chat está usando otro. */
  fallback: boolean
  reason: string | null
}

export interface LlmProvidersResponse {
  providers: LlmProviderOption[]
  configured: ConfiguredLlm
}

/**
 * Catálogo de proveedores de LLM (`GET /agents/llm/providers`).
 *
 * La disponibilidad no es una constante del FE: depende de la máquina —si el
 * SDK está instalado, si hay API key, si el servidor local responde y qué
 * modelos tiene descargados—, y por eso la decide el backend en cada consulta.
 */
export function useLlmProviders() {
  return useQuery({
    queryKey: ["llm-providers"],
    queryFn: async () => {
      const { data } = await apiClient.get<LlmProvidersResponse>("/agents/llm/providers")
      return data
    },
    staleTime: 30000,
  })
}

export interface ChatClearResponse {
  message: string
  /** Mensajes borrados del historial del servidor (2 por turno). 0 si ya estaba vacío. */
  cleared: number
}

/**
 * Limpia el historial de conversación del servidor (`POST /agents/chat/clear`).
 *
 * El historial vive en memoria del proceso: vaciar sólo el estado local deja al
 * agente recordando turnos que el usuario cree borrados. Idempotente — sobre un
 * historial ya vacío responde 200 con `cleared: 0`.
 */
export function useAgentChatClear() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post<ChatClearResponse>("/agents/chat/clear")
      return data
    },
  })
}

export function useSystemStatistics() {
  return useQuery({
    queryKey: ["system-statistics"],
    queryFn: async () => {
      const { data } = await apiClient.get("/agents/insights/statistics")
      return data
    },
  })
}

export function useTopRiskDocuments(limit: number = 10) {
  return useQuery({
    queryKey: ["top-risk-documents", limit],
    queryFn: async () => {
      const { data } = await apiClient.get(`/agents/insights/top-risk?limit=${limit}`)
      return data
    },
  })
}

export function useTransparencyTrends(startYear: number = 2025, startMonth: number = 1) {
  return useQuery({
    queryKey: ["transparency-trends", startYear, startMonth],
    queryFn: async () => {
      const { data } = await apiClient.get(
        `/agents/insights/trends?start_year=${startYear}&start_month=${startMonth}`
      )
      return data
    },
  })
}
