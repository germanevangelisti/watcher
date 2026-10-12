/**
 * Selector de proveedor del chat (`story-watcher-chat-llm-selector`).
 *
 * Lo que se prueba acá es que la pantalla no mienta sobre quién escribió una
 * respuesta: un selector de proveedores que no dice cuál se usó no sirve para
 * comparar calidad, y una burbuja que declara un modelo cuando la escribió el
 * sistema es peor que no declarar nada.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { AgentsDashboard } from "@/pages/analisis/agents-dashboard"
import {
  blockedProvidersLine,
  llmCredit,
  providerAvailabilityLine,
  providerOptionLabel,
  readStoredSelection,
  storeSelection,
} from "@/lib/llm-providers"
import type { ChatLlm, LlmProviderOption } from "@/lib/api"

const mutateAsync = vi.fn()
const clearAsync = vi.fn()

/** Catálogo del caso real de esta máquina: local sano, Gemini con SDK, Claude sin key. */
const CATALOGO = {
  providers: [
    {
      id: "ollama",
      label: "Ollama",
      local: true,
      available: true,
      reason: null,
      model: "qwen2.5:7b",
      models: ["qwen2.5:7b", "qwen2.5:14b"],
    },
    {
      id: "google",
      label: "Google Gemini",
      local: false,
      available: true,
      reason: "remoto: el contexto del boletín sale de la máquina",
      model: "gemini-2.5-flash",
      models: [],
    },
    {
      id: "anthropic",
      label: "Anthropic Claude",
      local: false,
      available: false,
      reason: "falta ANTHROPIC_API_KEY",
      model: "claude-3-5-sonnet-20241022",
      models: [],
    },
  ],
  configured: {
    provider: "ollama",
    model: "qwen2.5:7b",
    requested: "google",
    origin: "LLM_PROVIDER=google",
    fallback: true,
    reason: "google no se pudo construir: falta GOOGLE_API_KEY; el chat usa Ollama local, no sale nada de la máquina",
  },
}

let catalogo: unknown = CATALOGO
let cargando = false
let conError = false

vi.mock("@/lib/api", () => ({
  useAgentHealth: () => ({ data: undefined, isLoading: false, refetch: vi.fn() }),
  useSystemStatistics: () => ({ data: undefined, isLoading: false }),
  useTopRiskDocuments: () => ({ data: [], isLoading: false }),
  useTransparencyTrends: () => ({ isLoading: false }),
  useLlmProviders: () => ({ data: catalogo, isLoading: cargando, isError: conError }),
  useAgentChat: () => ({ mutateAsync, isPending: false }),
  useAgentChatClear: () => ({ mutateAsync: clearAsync, isPending: false }),
}))

const PREGUNTA = "¿Qué organismos concentran mayor gasto?"
const RESPUESTA = "Los tres primeros concentran el 40% del publicado."

function openChatTab() {
  render(<AgentsDashboard />)
  const tab = screen.getByRole("tab", { name: "Chat con Insights" })
  fireEvent.mouseDown(tab)
  fireEvent.keyDown(tab, { key: "Enter" })
  fireEvent.click(tab)
}

async function enviar(texto: string) {
  fireEvent.change(screen.getByPlaceholderText("Escribe tu consulta..."), {
    target: { value: texto },
  })
  fireEvent.click(screen.getByRole("button", { name: /Enviar/ }))
  await waitFor(() => expect(screen.getByText(RESPUESTA)).toBeTruthy())
}

beforeEach(() => {
  catalogo = CATALOGO
  cargando = false
  conError = false
  window.localStorage.clear()
  mutateAsync.mockReset()
  mutateAsync.mockResolvedValue({ response: RESPUESTA, data_used: [], llm: null })
  clearAsync.mockReset()
  clearAsync.mockResolvedValue({ message: "ok", cleared: 0 })
})

// ------------------------------------------------- la tarjeta (lógica pura)

describe("el texto de las opciones dice qué se está eligiendo", () => {
  const opciones = CATALOGO.providers as LlmProviderOption[]

  it("el modelo local va en la etiqueta: 7B y 14B son dos calidades distintas", () => {
    expect(providerOptionLabel(opciones[0])).toBe("Ollama · qwen2.5:7b")
    expect(providerOptionLabel({ ...opciones[0], model: "qwen2.5:14b" })).toBe(
      "Ollama · qwen2.5:14b",
    )
  })

  it("el local dice que nada sale de la máquina y el remoto dice lo contrario", () => {
    expect(providerAvailabilityLine(opciones[0])).toContain("nada sale de la máquina")
    expect(providerAvailabilityLine({ ...opciones[1], reason: null })).toContain(
      "sale de la máquina",
    )
  })

  it("un proveedor que no se puede usar muestra el motivo del backend, no un «no disponible»", () => {
    expect(providerAvailabilityLine(opciones[2])).toBe("falta ANTHROPIC_API_KEY")
  })

  it("abajo de la elección se lee qué le falta a los otros", () => {
    expect(blockedProvidersLine(opciones, "ollama")).toBe("Anthropic Claude: falta ANTHROPIC_API_KEY")
    // Al elegir Claude, su propio motivo no se repite; el que falta es el suyo.
    expect(blockedProvidersLine(opciones, "anthropic")).toBe("")
  })

  it("los remotos disponibles no se listan como bloqueados", () => {
    // Gemini está disponible: tiene SDK y key. Su aviso de "remoto" ya lo dice la
    // línea principal cuando se lo elige, y repetirlo acá sería ruido.
    expect(blockedProvidersLine(opciones, "ollama")).not.toContain("Gemini")
  })
})

// ------------------------------------------------------ el crédito de la burbuja

describe("el crédito de la burbuja", () => {
  const opciones = CATALOGO.providers as LlmProviderOption[]

  it("nombra proveedor y modelo cuando el modelo la redactó", () => {
    const llm: ChatLlm = { provider: "ollama", model: "qwen2.5:7b" }
    // El nombre sale del catálogo: la burbuja dice `Ollama`, no `ollama`.
    expect(llmCredit(llm, opciones)).toBe("Redactado con Ollama · qwen2.5:7b")
  })

  it("un proveedor que ya no está en el catálogo se muestra crudo, no inventado", () => {
    const llm: ChatLlm = { provider: "un-proveedor-viejo", model: "x" }
    expect(llmCredit(llm, opciones)).toBe("Redactado con un-proveedor-viejo · x")
  })

  it("dice que la escribió el sistema cuando el backend manda null", () => {
    // `null` no es "sin dato": es "no la escribió un modelo" (cortesía o fallback).
    expect(llmCredit(null, opciones)).toBe("Sin modelo: respuesta del sistema")
  })

  it("no declara nada si el backend no manda el campo (contrato viejo)", () => {
    expect(llmCredit(undefined, opciones)).toBeNull()
  })
})

// ------------------------------------------------------ la elección recordada

describe("la elección se recuerda entre sesiones", () => {
  it("guarda y recupera proveedor y modelo", () => {
    storeSelection({ provider: "ollama", model: "qwen2.5:14b" })
    expect(readStoredSelection()).toEqual({ provider: "ollama", model: "qwen2.5:14b" })
  })

  it("sin nada guardado devuelve null y no inventa una elección", () => {
    expect(readStoredSelection()).toBeNull()
  })

  it("un valor corrupto no rompe el panel", () => {
    window.localStorage.setItem("watcher.chat.llm", "{no soy json")
    expect(readStoredSelection()).toBeNull()
  })

  it("un objeto sin proveedor no cuenta como elección", () => {
    window.localStorage.setItem("watcher.chat.llm", JSON.stringify({ model: "qwen2.5:14b" }))
    expect(readStoredSelection()).toBeNull()
  })

  it("si el navegador no deja guardar, el selector sigue funcionando", () => {
    const original = window.localStorage.setItem
    window.localStorage.setItem = () => {
      throw new Error("datos de sitio bloqueados")
    }
    try {
      expect(() => storeSelection({ provider: "ollama" })).not.toThrow()
    } finally {
      window.localStorage.setItem = original
    }
  })
})

// ------------------------------------------------------ la tarjeta en pantalla

describe("la tarjeta del proveedor en el chat", () => {
  it("arranca mostrando el proveedor que el entorno está usando", () => {
    openChatTab()
    // El default deja de ser invisible: es el valor inicial del selector.
    expect(screen.getByTestId("chat-llm-select").textContent).toContain("Ollama · qwen2.5:7b")
  })

  it("dice de dónde sale el default y avisa si lo configurado cayó a local", () => {
    openChatTab()
    const origen = screen.getByTestId("chat-llm-origin").textContent ?? ""
    expect(origen).toContain("LLM_PROVIDER=google")
    expect(origen).toContain("no sale nada de la máquina")
  })

  it("explica qué le falta al proveedor que no se puede elegir", () => {
    openChatTab()
    expect(screen.getByTestId("chat-llm-hint").textContent).toContain(
      "Anthropic Claude: falta ANTHROPIC_API_KEY",
    )
  })

  it("el turno viaja con el proveedor elegido", async () => {
    openChatTab()
    mutateAsync.mockResolvedValue({
      response: RESPUESTA,
      data_used: [],
      llm: { provider: "ollama", model: "qwen2.5:7b" },
    })

    await enviar(PREGUNTA)

    expect(mutateAsync).toHaveBeenCalledWith({
      query: PREGUNTA,
      provider: "ollama",
      model: "qwen2.5:7b",
    })
  })

  it("cada burbuja declara con qué se redactó", async () => {
    openChatTab()
    mutateAsync.mockResolvedValue({
      response: RESPUESTA,
      data_used: [],
      llm: { provider: "ollama", model: "qwen2.5:7b" },
    })

    await enviar(PREGUNTA)

    expect(screen.getByTestId("chat-llm-credit").textContent).toBe(
      "Redactado con Ollama · qwen2.5:7b",
    )
  })

  it("una burbuja sin modelo no declara un proveedor que no la escribió", async () => {
    openChatTab()
    mutateAsync.mockResolvedValue({ response: RESPUESTA, data_used: [], llm: null })

    await enviar(PREGUNTA)

    expect(screen.getByTestId("chat-llm-credit").textContent).toBe(
      "Sin modelo: respuesta del sistema",
    )
  })

  it("un backend viejo sin `llm` no agrega ninguna línea", async () => {
    openChatTab()
    mutateAsync.mockResolvedValue({ response: RESPUESTA, data_used: [] })

    await enviar(PREGUNTA)

    expect(screen.queryByTestId("chat-llm-credit")).toBeNull()
  })

  it("el 400 del proveedor elegido se muestra con su motivo, no como un error genérico", async () => {
    openChatTab()
    mutateAsync.mockRejectedValue({
      response: { data: { detail: "No se pudo usar google: GOOGLE_API_KEY not found" } },
    })

    fireEvent.change(screen.getByPlaceholderText("Escribe tu consulta..."), {
      target: { value: PREGUNTA },
    })
    fireEvent.click(screen.getByRole("button", { name: /Enviar/ }))

    await waitFor(() =>
      expect(screen.getByText(/GOOGLE_API_KEY not found/)).toBeTruthy(),
    )
    expect(screen.queryByText(/No se pudo obtener respuesta del agente/)).toBeNull()
    // Una burbuja de error no declara proveedor: no hubo respuesta.
    expect(screen.queryByTestId("chat-llm-credit")).toBeNull()
  })

  it("si el catálogo no se pudo leer, no finge un proveedor", () => {
    conError = true
    openChatTab()

    expect(screen.getByTestId("chat-llm-error")).toBeTruthy()
    // Sin catálogo no hay disponibilidad que afirmar ni motivo que mostrar.
    expect(screen.queryByTestId("chat-llm-hint")).toBeNull()
    expect(screen.queryByTestId("chat-llm-select")).toBeNull()
  })

  it("mientras carga lo dice en vez de mostrar un selector vacío", () => {
    cargando = true
    openChatTab()

    expect(screen.getByTestId("chat-llm-loading")).toBeTruthy()
    expect(screen.queryByTestId("chat-llm-select")).toBeNull()
  })
})
