import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { ChatMarkdown } from "@/components/features/chat-markdown"

/**
 * El agente contesta en Markdown y la burbuja lo mostraba crudo: la captura de
 * Germán tenía los `**`, los `*` y los `>` a la vista. Acá se fija que se
 * rendericen, con el texto real de esa respuesta como caso principal.
 *
 * El contenido de la respuesta es no confiable: viene del modelo y de la DB, así
 * que se verifica también que no pueda inyectar HTML.
 */

const RESPUESTA_REAL = `Según los datos registrados como **proxy de Boletín Oficial (BO)**, el porcentaje ejecutado es el siguiente:

* **Ejecución (pagos publicados en BO):** **0,09%** del presupuesto vigente anual (ARS 6.869,13 millones sobre un total vigente de ARS 7.531.907,15 millones).
* *(Dato complementario)* **Compromisos publicados en BO** (llamados, adjudicaciones y contratos): representan el **23,49%** del presupuesto vigente anual (ARS 1.769.540,40 millones).

> **Aclaraciones metodológicas:**
> 1. **Período cubierto:** Los datos corresponden al período **febrero a septiembre de 2026** (8 de 12 meses; enero se encuentra pendiente de ingesta). El porcentaje se calcula contra el total anual sin prorratear.
> 2. **Fuente:** Los montos corresponden a lo **publicado en el Boletín Oficial** (proxy BO) y **no** equivalen al Devengado oficial de la Contaduría ni a registros de caja.`

function mount(content: string) {
  return render(<ChatMarkdown content={content} />).container
}

describe("ChatMarkdown — la respuesta real del agente", () => {
  it("no deja ningún marcador de Markdown a la vista", () => {
    const el = mount(RESPUESTA_REAL)

    expect(el.textContent).not.toContain("**")
    expect(el.textContent).not.toContain(">")
  })

  it("renderiza la negrita como negrita", () => {
    const el = mount(RESPUESTA_REAL)

    const strongs = Array.from(el.querySelectorAll("strong")).map((s) => s.textContent)
    expect(strongs).toContain("proxy de Boletín Oficial (BO)")
    expect(strongs).toContain("0,09%")
    expect(strongs).toContain("23,49%")
  })

  it("renderiza la cursiva sin comerse los asteriscos", () => {
    const el = mount(RESPUESTA_REAL)

    // Los paréntesis quedan fuera del énfasis; solo el texto va en cursiva.
    expect(el.querySelector("em")?.textContent).toBe("(Dato complementario)")
  })

  it("los bullets salen como lista, no como texto con asteriscos", () => {
    const el = mount(RESPUESTA_REAL)

    const items = el.querySelectorAll("ul > li")
    expect(items).toHaveLength(2)
    expect(items[0].textContent).toContain("Ejecución (pagos publicados en BO)")
  })

  it("la cita lleva la lista numerada adentro", () => {
    const el = mount(RESPUESTA_REAL)

    const cita = el.querySelector("blockquote")
    expect(cita).not.toBeNull()
    expect(cita!.textContent).toContain("Aclaraciones metodológicas")

    const numerados = cita!.querySelectorAll("ol > li")
    expect(numerados).toHaveLength(2)
    expect(numerados[0].textContent).toContain("Período cubierto")
    expect(numerados[1].textContent).toContain("Fuente")
  })

  it("conserva los montos y su formato original", () => {
    const el = mount(RESPUESTA_REAL)

    expect(el.textContent).toContain("ARS 7.531.907,15 millones")
    expect(el.textContent).toContain("8 de 12 meses")
  })
})

describe("ChatMarkdown — casos borde", () => {
  it("el texto plano pasa tal cual (no rompe el caso sin Markdown)", () => {
    const el = mount("El 12% del vigente.")

    expect(el.textContent).toBe("El 12% del vigente.")
    expect(el.querySelectorAll("p")).toHaveLength(1)
  })

  it("no interpreta el guión bajo: rompería campos como monto_vigente_total", () => {
    const el = mount("El campo monto_vigente_total no lleva cursiva.")

    expect(el.querySelector("em")).toBeNull()
    expect(el.textContent).toContain("monto_vigente_total")
  })

  it("escapa el HTML: la respuesta del modelo no inyecta marcado", () => {
    const el = mount('Ojo <img src=x onerror="alert(1)"> acá')

    expect(el.querySelector("img")).toBeNull()
    expect(el.textContent).toContain("<img src=x")
  })

  it("los encabezados quedan como texto en negrita, no como h1", () => {
    const el = mount("## Resumen\n\nTodo bien.")

    expect(el.querySelector("h1, h2, h3")).toBeNull()
    // Se degrada a un párrafo en negrita: un h1 no entra en una burbuja.
    const parrafo = el.querySelector("p")
    expect(parrafo?.textContent).toBe("Resumen")
    expect(parrafo?.className).toContain("font-semibold")
  })

  it("código inline", () => {
    const el = mount("Corré `make test` antes.")

    expect(el.querySelector("code")?.textContent).toBe("make test")
  })

  it("cambiar de viñeta a numeración abre otra lista", () => {
    const el = mount("- uno\n1. dos\n")

    expect(el.querySelectorAll("ul > li")).toHaveLength(1)
    expect(el.querySelectorAll("ol > li")).toHaveLength(1)
  })

  it("una respuesta vacía no explota", () => {
    const el = mount("")

    expect(el.textContent).toBe("")
  })
})

// ------------------------------------------------------- integración: la burbuja

const mutateAsync = vi.fn()

vi.mock("@/lib/api", () => ({
  useAgentHealth: () => ({ data: undefined, isLoading: false, refetch: vi.fn() }),
  useSystemStatistics: () => ({ data: undefined, isLoading: false }),
  useTopRiskDocuments: () => ({ data: [], isLoading: false }),
  useTransparencyTrends: () => ({ isLoading: false }),
  useAgentChat: () => ({ mutateAsync, isPending: false }),
}))

describe("la burbuja del asistente renderiza el Markdown", () => {
  beforeEach(() => {
    mutateAsync.mockReset()
    mutateAsync.mockResolvedValue({ response: "El **12%** del vigente." })
  })

  it("envía la consulta y muestra la negrita, no los asteriscos", async () => {
    const { AgentsDashboard } = await import("@/pages/analisis/agents-dashboard")
    render(<AgentsDashboard />)

    const tab = screen.getByRole("tab", { name: "Chat con Insights" })
    fireEvent.mouseDown(tab)
    fireEvent.click(tab)

    fireEvent.change(screen.getByPlaceholderText("Escribe tu consulta..."), {
      target: { value: "¿cuánto se ejecutó?" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Enviar/ }))

    await waitFor(() => expect(screen.getByText("12%")).toBeTruthy())
    expect(screen.getByText("12%").tagName).toBe("STRONG")
    expect(document.body.textContent).not.toContain("**")
  })
})
