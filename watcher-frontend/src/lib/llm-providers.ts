/**
 * Selección del proveedor de LLM del chat: estado recordado y copy de la tarjeta.
 *
 * Vive aparte del componente porque son decisiones que se prueban solas: qué se
 * recuerda entre sesiones, qué dice cada opción del selector y —sobre todo— qué
 * se declara cuando el backend **no** informa quién redactó una respuesta.
 *
 * El contexto del chat son boletines oficiales de una provincia: elegir un
 * proveedor remoto los manda afuera de la máquina. Por eso lo remoto no es un
 * detalle técnico del selector sino una advertencia que se ve.
 */

import type { ChatLlm, LlmProviderOption } from "@/lib/api/hooks/use-agents"

/** Elección explícita del usuario en la tarjeta. */
export interface ChatLlmSelection {
  provider: string
  model?: string
}

const STORAGE_KEY = "watcher.chat.llm"

/**
 * La elección se recuerda entre sesiones **si el navegador deja**.
 *
 * `localStorage` puede no existir o tirar (ventana privada, datos de sitio
 * bloqueados, modo restringido). Ninguna de esas es razón para que el panel deje
 * de renderizar: sin lo recordado, el selector arranca en el proveedor que el
 * entorno tenga configurado, que es lo que hacía antes de existir la tarjeta.
 */
export function readStoredSelection(): ChatLlmSelection | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null

    const parsed = JSON.parse(raw) as Partial<ChatLlmSelection>
    if (!parsed || typeof parsed.provider !== "string" || !parsed.provider) return null

    return {
      provider: parsed.provider,
      ...(typeof parsed.model === "string" && parsed.model ? { model: parsed.model } : {}),
    }
  } catch {
    return null
  }
}

export function storeSelection(selection: ChatLlmSelection): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(selection))
  } catch {
    // Sin persistencia el selector sigue funcionando en esta sesión.
  }
}

/**
 * Texto de una opción del selector.
 *
 * El modelo va en la etiqueta porque en local **es** la comparación: `qwen2.5:7b`
 * y `qwen2.5:14b` son dos calidades distintas del mismo proveedor, y quien mira
 * la lista tiene que poder distinguirlas antes de elegir.
 */
export function providerOptionLabel(provider: LlmProviderOption): string {
  return provider.model ? `${provider.label} · ${provider.model}` : provider.label
}

/**
 * La línea de arriba: qué implica el proveedor elegido.
 *
 * Para el local dice que nada sale de la máquina, y para los remotos dice lo
 * contrario. Un proveedor sin disponibilidad muestra su motivo —el mismo que
 * manda el backend— en lugar de un "no disponible" mudo.
 */
export function providerAvailabilityLine(provider: LlmProviderOption): string {
  if (!provider.available) return provider.reason ?? `${provider.label} no está disponible.`

  return provider.local
    ? "Local, off-line: nada sale de la máquina."
    : "Remoto: el contexto de los boletines sale de la máquina."
}

/**
 * Lo que falta para poder usar los otros: la razón por la que el selector no sirve
 * para comparar si alguna opción no se puede elegir.
 */
export function blockedProvidersLine(
  providers: LlmProviderOption[],
  selectedId: string,
): string {
  return providers
    .filter((p) => p.id !== selectedId && !p.available && p.reason)
    .map((p) => `${p.label}: ${p.reason}`)
    .join(" · ")
}

/**
 * El crédito de una burbuja: quién escribió esa respuesta.
 *
 * Distingue tres casos, y la distinción es el punto:
 * - el backend no manda `llm` → `null`, no se dice nada (contrato viejo);
 * - `llm: null` → la escribió el sistema, no un modelo ("gracias" o el texto de
 *   fallback cuando el modelo no contestó);
 * - `llm` con datos → el proveedor y el modelo que la redactaron.
 *
 * El nombre se resuelve contra el catálogo —la burbuja dice `Ollama`, no
 * `ollama`—, y si el proveedor ya no está en la lista se muestra su id: es
 * preferible un nombre crudo a un crédito inventado.
 */
export function llmCredit(
  llm?: ChatLlm | null,
  providers: LlmProviderOption[] = [],
): string | null {
  if (llm === undefined) return null

  const partes = [
    providers.find((p) => p.id === llm?.provider)?.label ?? llm?.provider,
    llm?.model,
  ].filter(Boolean)

  return partes.length > 0
    ? `Redactado con ${partes.join(" · ")}`
    : "Sin modelo: respuesta del sistema"
}
