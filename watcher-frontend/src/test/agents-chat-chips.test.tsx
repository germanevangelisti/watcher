import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { AgentsDashboard } from "@/pages/analisis/agents-dashboard"

const mutateAsync = vi.fn()

vi.mock("@/lib/api", () => ({
  useAgentHealth: () => ({ data: undefined, isLoading: false, refetch: vi.fn() }),
  useSystemStatistics: () => ({ data: undefined, isLoading: false }),
  useTopRiskDocuments: () => ({ data: [], isLoading: false }),
  useTransparencyTrends: () => ({ isLoading: false }),
  useAgentChat: () => ({ mutateAsync, isPending: false }),
}))

const CHIPS = [
  "¿Qué porcentaje del presupuesto vigente se ha ejecutado?",
  "¿Qué organismos concentran mayor gasto?",
  "¿Qué finalidades presentan mayor desvío?",
]

function openChatTab() {
  render(<AgentsDashboard />)
  const tab = screen.getByRole("tab", { name: "Chat con Insights" })
  // Radix Tabs activa con mouseDown/keyboard, no con click sintético
  fireEvent.mouseDown(tab)
  fireEvent.keyDown(tab, { key: "Enter" })
  fireEvent.click(tab)
}

beforeEach(() => {
  mutateAsync.mockReset()
  mutateAsync.mockResolvedValue({ response: "El 12% del vigente." })
})

describe("Chat con Insights — empty state chips", () => {
  it("no muestra chips en la tab Agentes (default)", () => {
    render(<AgentsDashboard />)
    expect(screen.queryByTestId("chat-suggestions")).toBeNull()
  })

  it("muestra exactamente los 3 chips con copy literal cuando no hay mensajes", () => {
    openChatTab()
    const chips = screen.getByTestId("chat-suggestions").querySelectorAll("button")
    expect(Array.from(chips).map((b) => b.textContent)).toEqual(CHIPS)
  })

  it("click en un chip envía la pregunta como el botón Enviar y oculta los chips", async () => {
    openChatTab()
    fireEvent.click(screen.getByRole("button", { name: CHIPS[0] }))

    expect(mutateAsync).toHaveBeenCalledWith(CHIPS[0])
    await waitFor(() => expect(screen.getByText("El 12% del vigente.")).toBeTruthy())
    // El mensaje del usuario queda en el historial y los chips ya no se muestran
    expect(screen.getByText(CHIPS[0])).toBeTruthy()
    expect(screen.queryByTestId("chat-suggestions")).toBeNull()
  })
})
