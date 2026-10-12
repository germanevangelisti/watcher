import type { Clasificacion } from "@/types/precio-mercado"

const ars = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 2 })

export function formatArs(value: number | null | undefined): string {
  return value == null ? "-" : ars.format(value)
}

export const CLASIFICACION_LABEL: Record<Clasificacion, string> = {
  dentro_de_rango: "Dentro de rango",
  observable: "Observable",
  alerta: "Alerta",
  sin_datos_suficientes: "Sin datos suficientes",
}
