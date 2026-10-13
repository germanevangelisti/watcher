import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, renderHook, screen, fireEvent, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { AgentsDashboard } from "@/pages/analisis/agents-dashboard"

/**
 * Historia `chat-turn-memory`: el path de chat no escribía historial server-side y
 * `POST /agents/chat/clear` existía sin UI. Acá se fija el control del FE: limpia
 * la conversación en pantalla **y** el historial del servidor, y si el servidor no
 * confirma el borrado lo dice en vez de mentir con un chat vacío.
 */

const mutateAsync = vi.fn()
const clearAsync = vi.fn()

vi.mock("@/lib/api", () => ({
  useAgentHealth: () => ({ data: undefined, isLoading: false, refetch: vi.fn() }),
  useSystemStatistics: () => ({ data: undefined, isLoading: false }),
  useTopRiskDocuments: () => ({ data: [], isLoading: false }),
  useTransparencyTrends: () => ({ isLoading: false }),
  useLlmProviders: () => ({ data: undefined, isLoading: false, isError: false }),
  useAgentChat: () => ({ mutateAsync, isPending: false }),
  useAgentChatClear: () => ({ mutateAsync: clearAsync, isPending: false }),
}))

const PREGUNTA = "¿Qué organismos concentran mayor gasto?"

function openChatTab() {
  render(<AgentsDashboard />)
  const tab = screen.getByRole("tab", { name: "Chat con Insights" })
  // Radix Tabs activa con mouseDown/keyboard, no con click sintético
  fireEvent.mouseDown(tab)
  fireEvent.keyDown(tab, { key: "Enter" })
  fireEvent.click(tab)
}

function clearButton() {
  return screen.getByTestId("chat-clear") as HTMLButtonElement
}

async function send(text: string) {
  fireEvent.change(screen.getByPlaceholderText("Escribe tu consulta..."), {
    target: { value: text },
  })
  fireEvent.click(screen.getByRole("button", { name: /Enviar/ }))
  await waitFor(() => expect(screen.getByText("El 12% del vigente.")).toBeTruthy())
}

beforeEach(() => {
  mutateAsync.mockReset()
  mutateAsync.mockResolvedValue({ response: "El 12% del vigente." })
  clearAsync.mockReset()
  clearAsync.mockResolvedValue({ message: "Historial limpiado", cleared: 2 })
})

describe("Chat con Insights — Limpiar chat", () => {
  it("sin mensajes el control está deshabilitado (no hay nada que limpiar)", () => {
    openChatTab()
    expect(clearButton().disabled).toBe(true)
  })

  it("limpia la pantalla, vacía el input y llama al endpoint del servidor", async () => {
    openChatTab()
    await send(PREGUNTA)
    expect(clearButton().disabled).toBe(false)

    fireEvent.change(screen.getByPlaceholderText("Escribe tu consulta..."), {
      target: { value: "borrador sin enviar" },
    })
    fireEvent.click(clearButton())

    // El historial local se vacía en el acto: vuelven el empty state y los chips.
    await waitFor(() => expect(screen.getByTestId("chat-suggestions")).toBeTruthy())
    expect(screen.queryByText("El 12% del vigente.")).toBeNull()
    // ...y el servidor se entera.
    expect(clearAsync).toHaveBeenCalledTimes(1)
    // El borrador tampoco sobrevive a un "limpiar chat".
    expect((screen.getByPlaceholderText("Escribe tu consulta...") as HTMLInputElement).value).toBe("")
  })

  it("si el servidor no confirma el borrado, lo declara y deja reintentar", async () => {
    clearAsync.mockRejectedValue(new Error("500"))
    openChatTab()
    await send(PREGUNTA)

    fireEvent.click(clearButton())

    // La pantalla se limpió igual...
    await waitFor(() => expect(screen.getByTestId("chat-suggestions")).toBeTruthy())
    // ...pero no se finge que el agente olvidó: el hueco se declara.
    const aviso = screen.getByTestId("chat-clear-error")
    expect(aviso.textContent).toContain("puede seguir recordando")
    // Y el control sigue disponible para reintentar.
    expect(clearButton().disabled).toBe(false)
  })

  it("un segundo clear sin mensajes nuevos vuelve a estar deshabilitado", async () => {
    openChatTab()
    await send(PREGUNTA)
    fireEvent.click(clearButton())
    await waitFor(() => expect(screen.getByTestId("chat-suggestions")).toBeTruthy())

    expect(clearButton().disabled).toBe(true)
    expect(clearAsync).toHaveBeenCalledTimes(1)
  })
})

// ------------------------------------------------- contrato del hook (no ad-hoc)
//
// El criterio pide un hook exportado en vez de un fetch suelto dentro del
// componente: acá se fija la URL, el método y el tipado de la respuesta.

vi.mock("@/lib/api/client", () => ({
  default: { post: vi.fn() },
}))

describe("useAgentChatClear", () => {
  it("pega en POST /agents/chat/clear y devuelve los mensajes borrados", async () => {
    const client = (await import("@/lib/api/client")).default as unknown as {
      post: ReturnType<typeof vi.fn>
    }
    client.post.mockResolvedValue({ data: { message: "Historial limpiado", cleared: 4 } })

    const { useAgentChatClear } = await import("@/lib/api/hooks/use-agents")
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useAgentChatClear(), { wrapper })
    const data = await result.current.mutateAsync()

    expect(client.post).toHaveBeenCalledWith("/agents/chat/clear")
    expect(data.cleared).toBe(4)
  })
})
