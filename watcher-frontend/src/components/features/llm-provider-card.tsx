import { Settings2 } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { LlmProvidersResponse } from "@/lib/api/hooks/use-agents"
import {
  blockedProvidersLine,
  providerAvailabilityLine,
  providerOptionLabel,
  type ChatLlmSelection,
} from "@/lib/llm-providers"

interface LlmProviderCardProps {
  /** Catálogo tal como lo publica el backend. `undefined` mientras carga. */
  catalog?: LlmProvidersResponse
  isLoading: boolean
  isError: boolean
  selection: ChatLlmSelection | null
  onChange: (selection: ChatLlmSelection) => void
}

/**
 * Selector del proveedor de LLM del chat (`story-watcher-chat-llm-selector`).
 *
 * Con qué proveedor contesta el chat salía de `LLM_PROVIDER` en el `.env`, que
 * no se ve desde ninguna pantalla: la única forma de saber si las respuestas las
 * escribía Gemini o el modelo local era leer el log del backend. Para comparar
 * calidad hay que poder elegir, y para elegir con criterio hay que ver qué está
 * disponible y qué le falta a lo que no.
 *
 * La disponibilidad la decide el backend, no esta tarjeta: depende de la máquina
 * (SDK instalado, API key, servidor local arriba, modelos descargados). Acá sólo
 * se muestra el motivo tal como llega.
 */
export function LlmProviderCard({
  catalog,
  isLoading,
  isError,
  selection,
  onChange,
}: LlmProviderCardProps) {
  const providers = catalog?.providers ?? []
  const configured = catalog?.configured

  // Mientras no haya elección, el selector muestra el proveedor que el entorno
  // está usando: el default deja de ser invisible incluso antes del primer clic.
  const selectedId = selection?.provider ?? configured?.provider ?? ""
  const selected = providers.find((p) => p.id === selectedId)
  const modelosDelElegido = selected?.models ?? []
  const selectedModel = selection?.model ?? selected?.model ?? undefined
  const bloqueados = blockedProvidersLine(providers, selectedId)

  const handleProviderChange = (providerId: string) => {
    const nuevo = providers.find((p) => p.id === providerId)
    // El modelo se elige por proveedor: arrastrar el de Ollama a Gemini mandaría
    // un nombre de modelo local a una API remota.
    onChange({ provider: providerId, ...(nuevo?.model ? { model: nuevo.model } : {}) })
  }

  return (
    <Card data-testid="chat-llm-card">
      <CardContent className="space-y-2 pt-4">
        <Label className="flex items-center gap-2 text-sm">
          <Settings2 className="h-4 w-4" />
          Proveedor del chat
        </Label>

        {isError ? (
          <p className="text-[11px] text-muted-foreground" data-testid="chat-llm-error">
            No se pudo leer el catálogo de proveedores. El chat sigue usando el que
            tenga configurado el backend.
          </p>
        ) : isLoading ? (
          <p className="text-[11px] text-muted-foreground" data-testid="chat-llm-loading">
            Leyendo los proveedores disponibles…
          </p>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <Select value={selectedId} onValueChange={handleProviderChange}>
                <SelectTrigger className="h-9 w-full sm:w-72" data-testid="chat-llm-select">
                  <SelectValue placeholder="Elegí un proveedor" />
                </SelectTrigger>
                <SelectContent>
                  {providers.map((provider) => (
                    <SelectItem
                      key={provider.id}
                      value={provider.id}
                      disabled={!provider.available}
                      data-testid={`chat-llm-option-${provider.id}`}
                    >
                      {providerOptionLabel(provider)}
                      {!provider.available && " — no disponible"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Segundo selector sólo para el local: 7B y 14B son dos calidades
                  del mismo proveedor, y compararlas es parte de lo pedido. */}
              {modelosDelElegido.length > 1 && (
                <Select
                  value={selectedModel}
                  onValueChange={(model) => onChange({ provider: selectedId, model })}
                >
                  <SelectTrigger className="h-9 w-full sm:w-56" data-testid="chat-llm-model">
                    <SelectValue placeholder="Modelo" />
                  </SelectTrigger>
                  <SelectContent>
                    {modelosDelElegido.map((model) => (
                      <SelectItem key={model} value={model}>
                        {model}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {selected && (
              <p className="text-[11px] text-muted-foreground" data-testid="chat-llm-hint">
                {providerAvailabilityLine(selected)}
                {bloqueados && <span> {bloqueados}.</span>}
              </p>
            )}

            {/* De dónde sale el proveedor con el que el chat arranca. Con el SDK
                de Google instalado, un `.env` que diga `LLM_PROVIDER=google`
                manda el contexto de los boletines afuera sin tocar una línea de
                código: que se lea acá es la diferencia entre elegir y enterarse. */}
            {configured && (
              <p className="text-[11px] text-muted-foreground" data-testid="chat-llm-origin">
                Por defecto: {configured.origin}
                {configured.fallback && configured.reason ? ` — ${configured.reason}` : ""}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
