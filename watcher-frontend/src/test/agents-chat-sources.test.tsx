import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react"
import { AgentsDashboard } from "@/pages/analisis/agents-dashboard"
import { chatSources, sourceLabel } from "@/lib/chat-sources"

/**
 * Historia `chat-cite-data-used`: el backend ya devolvía `data_used` y el FE lo
 * descartaba. Acá se fija que cada burbuja del asistente declare lo que el agente
 * consultó de verdad — claves estructuradas, nunca URLs inventadas— y que la
 * ausencia de fuentes se vea como ausencia, no se disfrace.
 */

const mutateAsync = vi.fn()

vi.mock("@/lib/api", () => ({
  useAgentHealth: () => ({ data: undefined, isLoading: false, refetch: vi.fn() }),
  useSystemStatistics: () => ({ data: undefined, isLoading: false }),
  useTopRiskDocuments: () => ({ data: [], isLoading: false }),
  useTransparencyTrends: () => ({ isLoading: false }),
  useLlmProviders: () => ({ data: undefined, isLoading: false, isError: false }),
  useAgentChat: () => ({ mutateAsync, isPending: false }),
  useAgentChatClear: () => ({ mutateAsync: vi.fn(), isPending: false }),
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

/** La burbuja del asistente que contiene la respuesta. */
function burbujaAsistente() {
  return screen.getByText(RESPUESTA).closest("[data-role='assistant']") as HTMLElement
}

beforeEach(() => {
  mutateAsync.mockReset()
  mutateAsync.mockResolvedValue({ response: RESPUESTA, data_used: ["ejecucion_resumen"] })
})

// ------------------------------------------------------------------ lib pura

describe("chatSources", () => {
  it("traduce las claves del backend a etiquetas legibles", () => {
    expect(sourceLabel("ejecucion_resumen")).toBe("Ejecución / resumen")
    expect(sourceLabel("finalidades")).toBe("Finalidades")
    expect(sourceLabel("red_flags")).toBe("Red flags")
    expect(sourceLabel("organismo_desglose")).toBe("Desglose por organismo")
  })

  it("no descarta una clave desconocida: la muestra sin guiones bajos", () => {
    expect(chatSources(["tool_nueva_del_backend"])).toEqual([
      { key: "tool_nueva_del_backend", label: "tool nueva del backend" },
    ])
  })

  it("la fuente del corpus no afirma una búsqueda semántica que puede no haber corrido", () => {
    // Los fragmentos son de `hybrid_search` (keyword + semántica fusionadas), y en
    // una máquina sin embeddings locales la única mitad que corre es la de keyword.
    expect(sourceLabel("corpus_boletines")).toBe("Boletines oficiales")
    // La clave vieja ya no está en el mapa: cae al fallback, sin reclamar nada.
    expect(sourceLabel("semantic_context")).toBe("semantic context")
  })

  it("conserva el orden de consulta y deduplica", () => {
    const fuentes = chatSources(["organismos", "finalidades", "organismos"])

    expect(fuentes.map((f) => f.key)).toEqual(["organismos", "finalidades"])
  })

  it("sin dato devuelve lista vacía, nunca null ni una fuente inventada", () => {
    expect(chatSources(undefined)).toEqual([])
    expect(chatSources(null)).toEqual([])
    expect(chatSources([])).toEqual([])
    expect(chatSources([""])).toEqual([])
  })
})

// ---------------------------------------------------------------------- UI

describe("Chat con Insights — citas por burbuja", () => {
  it("la burbuja del asistente muestra las fuentes consultadas", async () => {
    openChatTab()
    await enviar(PREGUNTA)

    const burbuja = burbujaAsistente()
    const fuentes = within(burbuja).getByTestId("chat-sources")
    expect(fuentes.textContent).toContain("Fuentes:")
    expect(within(fuentes).getByTestId("chat-source-ejecucion_resumen").textContent).toBe(
      "Ejecución / resumen"
    )
  })

  it("muestra todas las fuentes, en el orden en que se consultaron", async () => {
    mutateAsync.mockResolvedValue({
      response: RESPUESTA,
      data_used: ["ejecucion_resumen", "organismos", "finalidades"],
    })
    openChatTab()
    await enviar(PREGUNTA)

    const etiquetas = within(burbujaAsistente())
      .getAllByTestId(/^chat-source-/)
      .map((el) => el.textContent)
    expect(etiquetas).toEqual(["Ejecución / resumen", "Organismos", "Finalidades"])
  })

  it("el mensaje del usuario no lleva fuentes", async () => {
    openChatTab()
    await enviar(PREGUNTA)

    const burbuja = screen.getByText(PREGUNTA).closest("[data-role='user']") as HTMLElement
    expect(within(burbuja).queryByTestId("chat-sources")).toBeNull()
    // Y la única cita visible es la del asistente.
    expect(screen.getAllByTestId("chat-sources")).toHaveLength(1)
  })

  it("sin `data_used` el texto igual se renderiza (backend viejo, sin romper)", async () => {
    mutateAsync.mockResolvedValue({ response: RESPUESTA })
    openChatTab()

    await enviar(PREGUNTA)

    const burbuja = burbujaAsistente()
    expect(within(burbuja).getByText(RESPUESTA)).toBeTruthy()
    // La ausencia se declara: no se inventa una cita ni se omite el tema.
    expect(within(burbuja).getByTestId("chat-sources-empty").textContent).toContain(
      "Sin fuentes estructuradas"
    )
    expect(within(burbuja).queryAllByTestId(/^chat-source-/)).toHaveLength(0)
  })

  it("`data_used` vacío se trata igual que ausente", async () => {
    mutateAsync.mockResolvedValue({ response: RESPUESTA, data_used: [] })
    openChatTab()
    await enviar(PREGUNTA)

    const burbuja = burbujaAsistente()
    expect(within(burbuja).getByTestId("chat-sources-empty")).toBeTruthy()
    expect(within(burbuja).queryByTestId("chat-sources")).toBeNull()
  })

  it("una burbuja de error no declara fuentes: no hubo consulta", async () => {
    mutateAsync.mockRejectedValue(new Error("500"))
    openChatTab()

    fireEvent.change(screen.getByPlaceholderText("Escribe tu consulta..."), {
      target: { value: PREGUNTA },
    })
    fireEvent.click(screen.getByRole("button", { name: /Enviar/ }))

    await waitFor(() =>
      expect(screen.getByText("Error: No se pudo obtener respuesta del agente")).toBeTruthy()
    )
    const burbuja = screen
      .getByText("Error: No se pudo obtener respuesta del agente")
      .closest("[data-role='assistant']") as HTMLElement
    expect(within(burbuja).queryByTestId("chat-sources-empty")).toBeNull()
    expect(within(burbuja).queryByTestId("chat-sources")).toBeNull()
  })
})
