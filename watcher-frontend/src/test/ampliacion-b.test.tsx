import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { FinalidadesTechoCard } from "@/components/features/finalidades-techo"
import { ProxyBoPanel } from "@/components/features/proxy-bo-finalidad"
import { parseMoney } from "@/lib/presupuesto-format"
import type {
  FinalidadesResumen,
  ProxyBoResumen,
} from "@/types/presupuesto"

/**
 * El corte 2026 real, en millones de ARS (la unidad del API).  Los % y el ancla
 * ($7.531,91B) son los que compara la prueba manual: si el fixture y la pantalla
 * se despegara del corte, estos tests seguirían verdes y la prueba manual fallaría.
 */
const CORTE: FinalidadesResumen = {
  ejercicio: 2026,
  total_inicial: 7_531_910,
  total_vigente: 7_531_910,
  total_registros: 480,
  items: [
    {
      clave: "1",
      label: "Administración Gubernamental",
      count: 120,
      monto_inicial: 568_060,
      monto_vigente: 568_060,
      participacion_techo_pct: 7.54,
      detalle: [],
    },
    {
      clave: "2",
      label: "Servicios de Defensa y Seguridad",
      count: 60,
      monto_inicial: 268_190,
      monto_vigente: 268_190,
      participacion_techo_pct: 3.56,
      detalle: [],
    },
    {
      clave: "3",
      label: "Servicios Sociales",
      count: 180,
      monto_inicial: 2_388_350,
      monto_vigente: 2_388_350,
      participacion_techo_pct: 31.71,
      detalle: [],
    },
    {
      clave: "sin_clasificar",
      label: "Sin clasificar",
      count: 120,
      monto_inicial: 4_307_310,
      monto_vigente: 4_307_310,
      participacion_techo_pct: 57.19,
      detalle: [
        {
          clave: "4",
          label: "Servicios Económicos",
          count: 70,
          monto_inicial: 3_066_500,
          monto_vigente: 3_066_500,
          participacion_techo_pct: 40.71,
        },
        {
          clave: "sin_partida",
          label: "Partida vacía",
          count: 30,
          monto_inicial: 738_770,
          monto_vigente: 738_770,
          participacion_techo_pct: 9.81,
        },
        {
          clave: "Recursos",
          label: "Recursos",
          count: 8,
          monto_inicial: 183_810,
          monto_vigente: 183_810,
          participacion_techo_pct: 2.44,
        },
        {
          clave: "Cuentas",
          label: "Cuentas especiales",
          count: 6,
          monto_inicial: 168_530,
          monto_vigente: 168_530,
          participacion_techo_pct: 2.24,
        },
        {
          clave: "5",
          label: "Deuda Pública",
          count: 4,
          monto_inicial: 86_400,
          monto_vigente: 86_400,
          participacion_techo_pct: 1.15,
        },
        {
          clave: "6",
          // El `6` del anexo no está en el clasificador: sin label.
          label: null,
          count: 2,
          monto_inicial: 63_300,
          monto_vigente: 63_300,
          participacion_techo_pct: 0.84,
        },
      ],
    },
  ],
  honestidad: {
    es_techo: true,
    inicial_es_vigente: true,
    filas_inicial_distinto_vigente: 0,
    es_credito_modificado: false,
    incluye_devengado_cge: false,
    notas: [
      "Los montos son techo de la Ley 11.088 / Mapas: no hay ejecución acá.",
      "No es crédito modificado.",
      "No es Devengado CGE: no hay caja devengada en esta respuesta.",
    ],
  },
}

/**
 * El proxy del corte V.5.  La aritmética cierra a propósito y no es decorativa:
 * la suma de los ítems es `monto_con_programa` (448.000) y **no** `monto_total`
 * (852.520) — la diferencia es lo que no tiene programa, y es el dato que el
 * banner declara en vez de repartir.  Las etapas suman el total.
 */
const PROXY: ProxyBoResumen = {
  ejercicio: 2026,
  items: [
    {
      clave: "1",
      label: "Administración Gubernamental",
      count: 12,
      monto_publicado: 42_000,
      monto_techo: 568_060,
      pct_publicado_techo: 7.39,
      detalle: [],
    },
    {
      clave: "2",
      label: "Servicios de Defensa y Seguridad",
      count: 4,
      monto_publicado: 310_000,
      monto_techo: 268_190,
      pct_publicado_techo: 115.59,
      detalle: [],
    },
    {
      clave: "3",
      label: "Servicios Sociales",
      count: 0,
      monto_publicado: 0,
      monto_techo: 2_388_350,
      pct_publicado_techo: 0,
      detalle: [],
    },
    {
      clave: "sin_clasificar",
      label: "Sin clasificar",
      count: 18,
      monto_publicado: 96_000,
      monto_techo: 4_307_310,
      pct_publicado_techo: 2.23,
      detalle: [
        {
          clave: "4",
          label: "Servicios Económicos",
          count: 14,
          monto_publicado: 72_000,
          monto_techo: 3_066_500,
          pct_publicado_techo: 2.35,
        },
        {
          clave: "6",
          label: null,
          count: 4,
          monto_publicado: 24_000,
          monto_techo: 63_300,
          pct_publicado_techo: 37.91,
        },
      ],
    },
  ],
  cobertura: {
    monto_total: 852_520,
    monto_con_programa: 448_000,
    monto_sin_programa: 404_520,
    count_sin_programa: 364,
    pct_sin_programa: 47.45,
    monto_atribuido_finalidad: 424_000,
    monto_no_clasificado: 24_000,
    fecha_desde: "2026-05-01",
    fecha_hasta: "2026-09-30",
    denominador_es_anual: true,
  },
  etapas: [
    { clave: "llamado", label: "Llamado a licitación", monto: 851_320 },
    {
      clave: "compromiso_asumido",
      label: "Compromiso asumido (adjudicación + contrato)",
      monto: 1_200,
    },
    { clave: "pago", label: "Pago", monto: 0 },
    { clave: "sin_etapa", label: "Sin etapa clasificada", monto: 0 },
  ],
  honestidad: {
    es_proxy_bo: true,
    es_devengado: false,
    es_devengado_cge: false,
    etiqueta_numerador: "publicado en el BO",
    notas: [
      "Los montos son lo publicado en el BO (llamados, adjudicaciones, contratos y pagos) contra el techo de la Ley: no son ejecución presupuestaria.",
      "No es Devengado CGE: no hay caja devengada en esta respuesta.",
      "Lo que no tiene programa identificado no se reparte entre finalidades: se declara en la cobertura.",
    ],
  },
}

function texto(container: HTMLElement): string {
  return container.textContent ?? ""
}

describe("FinalidadesTechoCard", () => {
  it("muestra las 4 filas: 1, 2, 3 y el bucket, sin colapsar sin_clasificar", () => {
    render(<FinalidadesTechoCard data={CORTE} />)

    expect(screen.getByText("Administración Gubernamental")).toBeDefined()
    expect(screen.getByText("Servicios de Defensa y Seguridad")).toBeDefined()
    expect(screen.getByText("Servicios Sociales")).toBeDefined()
    // El bucket va al mismo nivel: es el 57,19% del techo, no un resto escondido.
    expect(screen.getByText("Sin clasificar")).toBeDefined()
    expect(screen.getByText("57.2%")).toBeDefined()
  })

  it("muestra el ancla del corte que compara la prueba manual", () => {
    const { container } = render(<FinalidadesTechoCard data={CORTE} />)

    // $7.531,91B: es-AR, no "$7531.91B".
    expect(texto(container)).toContain("$7.531,91B")
    expect(texto(container)).toContain("480 programas")
  })

  it("muestra el detalle del bucket para que el 57,19% sea legible", () => {
    render(<FinalidadesTechoCard data={CORTE} />)

    expect(screen.getByText("Servicios Económicos")).toBeDefined()
    expect(screen.getByText("Deuda Pública")).toBeDefined()
    expect(screen.getByText("Partida vacía")).toBeDefined()
  })

  it("cae a la clave cuando el componente no tiene label", () => {
    const { container } = render(<FinalidadesTechoCard data={CORTE} />)

    // El `6` del anexo: ni en blanco ni la palabra "null".
    expect(texto(container)).not.toContain("null")
    expect(screen.getByText("6")).toBeDefined()
  })

  it("los porcentajes de las 4 filas cierran el techo", () => {
    const total = CORTE.items.reduce(
      (acc, item) => acc + item.participacion_techo_pct,
      0
    )

    expect(total).toBeCloseTo(100, 2)
  })

  it("el detalle del bucket suma el bucket", () => {
    const bucket = CORTE.items.find((item) => item.clave === "sin_clasificar")!
    const suma = bucket.detalle.reduce(
      (acc, d) => acc + (parseMoney(d.monto_vigente) ?? 0),
      0
    )

    expect(suma).toBe(parseMoney(bucket.monto_vigente))
  })

  it("declara que no hay % de ejecución en este slice", () => {
    const { container } = render(<FinalidadesTechoCard data={CORTE} />)

    const t = texto(container)
    expect(t).not.toContain("% ejecutado")
    expect(t).not.toContain("% ejecución")
    expect(t).toContain("Es techo, no ejecución")
  })

  it("la suma de los ítems del proxy es lo atribuido, no el total publicado", () => {
    const suma = PROXY.items.reduce(
      (acc, item) => acc + (parseMoney(item.monto_publicado) ?? 0),
      0
    )

    expect(suma).toBe(parseMoney(PROXY.cobertura.monto_con_programa))
    expect(suma).not.toBe(parseMoney(PROXY.cobertura.monto_total))
  })

  it("las etapas del proxy suman el total publicado", () => {
    const suma = PROXY.etapas.reduce(
      (acc, etapa) => acc + (parseMoney(etapa.monto) ?? 0),
      0
    )

    expect(suma).toBe(parseMoney(PROXY.cobertura.monto_total))
  })
})

describe("FinalidadesTechoCard — disclaimer (Must)", () => {
  it("el disclaimer es visible sin interacción", () => {
    render(<FinalidadesTechoCard data={CORTE} />)

    // Sin tooltip, sin toggle: el texto está en el DOM al renderizar.
    expect(screen.getByText("Qué es y qué no es esta cifra")).toBeDefined()
    expect(screen.getByText("No es crédito modificado.")).toBeDefined()
    expect(
      screen.getByText(
        "No es Devengado CGE: no hay caja devengada en esta respuesta."
      )
    ).toBeDefined()
  })

  it("el titular sale del flag medido, no del copy", () => {
    render(<FinalidadesTechoCard data={CORTE} />)

    expect(screen.getByText(/Inicial = vigente/)).toBeDefined()
  })

  it("cambia el titular cuando el corte deja de sostener inicial = vigente", () => {
    // El test espejo del de backend: si el copy estuviera hardcodeado, la UI
    // seguiría afirmando "inicial = vigente" sobre un corte que ya tiene variación.
    const conVariacion: FinalidadesResumen = {
      ...CORTE,
      honestidad: {
        ...CORTE.honestidad,
        inicial_es_vigente: false,
        filas_inicial_distinto_vigente: 2,
        notas: [
          "Los montos son techo de la Ley 11.088 / Mapas: no hay ejecución acá.",
          "Inicial ≠ vigente en 2 filas: la variación NO es 0.",
          "No es crédito modificado.",
        ],
      },
    }

    const { container } = render(<FinalidadesTechoCard data={conVariacion} />)

    expect(texto(container)).toContain("Inicial ≠ vigente en 2 filas")
    expect(texto(container)).toContain("la variación NO es 0")
  })
})

describe("FinalidadesTechoCard — 404 declarado", () => {
  it("no renderiza ceros cuando el ejercicio no tiene Ley cargada", () => {
    const error = new Error(
      "no hay presupuesto_base cargado para el ejercicio 2027; no es techo $0, es un hueco"
    )

    const { container } = render(<FinalidadesTechoCard error={error} />)

    expect(screen.getByText(/Sin techo declarado para este ejercicio/)).toBeDefined()
    const t = texto(container)
    expect(t).toContain("hueco")
    expect(t).toContain("No es un techo de $0")
    // Y no cae en el estado vacío con cifras inventadas.
    expect(t).not.toContain("Sin clasificar")
  })
})

describe("ProxyBoPanel", () => {
  it("rotula el numerador como publicado en el BO, leyéndolo de la respuesta", () => {
    render(<ProxyBoPanel data={PROXY} />)

    expect(screen.getByText("publicado en el BO")).toBeDefined()
  })

  it("nunca llama Devengado al proxy: la única mención es la que lo niega", () => {
    const { container } = render(<ProxyBoPanel data={PROXY} />)

    const menciones = texto(container).match(/[^.]*devengado[^.]*/gi) ?? []
    expect(menciones.length).toBeGreaterThan(0)
    for (const mencion of menciones) {
      expect(mencion.toLowerCase()).toMatch(/no (es|hay|son)/)
    }
  })

  it("muestra el banner de cobertura y declara lo que no se reparte", () => {
    const { container } = render(<ProxyBoPanel data={PROXY} />)

    const t = texto(container)
    expect(t).toContain("Cobertura del proxy")
    expect(t).toContain("$404,52B")
    expect(t).toContain("364 actos")
    expect(t).toContain("No se reparten entre las finalidades")
  })

  it("declara que el denominador es anual y que no se prorratea", () => {
    const { container } = render(<ProxyBoPanel data={PROXY} />)

    const t = texto(container)
    expect(t).toContain("Ley anual completa")
    expect(t).toContain("No se prorratea la Ley")
    expect(t).toContain("2026-05-01 → 2026-09-30")
  })

  it("publica el >100% en vez de recortarlo", () => {
    const { container } = render(<ProxyBoPanel data={PROXY} />)

    expect(texto(container)).toContain(">100%")
    expect(screen.getByText("115.6%")).toBeDefined()
  })

  it("informa la composición por etapa sin restarla del total", () => {
    const { container } = render(<ProxyBoPanel data={PROXY} />)

    const t = texto(container)
    expect(t).toContain("Composición: en qué etapa del gasto está lo publicado")
    expect(t).toContain("Llamado a licitación")
    expect(t).toContain("Compromiso asumido (adjudicación + contrato)")
    expect(t).toContain("Un llamado a licitación publicado no es un compromiso asumido")
  })

  it("muestra el detalle del bucket del proxy, con la clave para el `6`", () => {
    const { container } = render(<ProxyBoPanel data={PROXY} />)

    expect(screen.getByText("Servicios Económicos")).toBeDefined()
    expect(texto(container)).not.toContain("null")
    expect(screen.getByText("6")).toBeDefined()
  })

  it("no renderiza el proxy sin techo como si fuera $0", () => {
    render(<ProxyBoPanel error={new Error("no es techo $0, es un hueco")} />)

    expect(screen.getByText(/Sin techo declarado para este ejercicio/)).toBeDefined()
    expect(screen.queryByText("publicado en el BO")).toBeNull()
  })
})
