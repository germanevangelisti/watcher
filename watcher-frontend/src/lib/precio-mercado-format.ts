import type { Clasificacion, Nivel, Objeto, TipoGasto } from "@/types/precio-mercado"

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

export const TIPO_GASTO_LABEL: Record<TipoGasto, string> = {
  licitacion: "Licitación",
  concurso_precios: "Concurso de precios",
  subasta_electronica: "Subasta electrónica",
  compra_directa: "Compra directa",
  contratacion: "Contratación",
  subsidio_transferencia: "Subsidio / transferencia",
  otro: "Otro",
  no_es_gasto: "No es gasto",
}

export const OBJETO_LABEL: Record<Objeto, string> = {
  obra: "Obra",
  bien: "Bienes",
  servicio: "Servicio",
  transferencia: "Transferencia",
  otro: "Otro",
  no_aplica: "—",
}

export const NIVEL_LABEL: Record<Nivel, string> = {
  provincial: "Provincia",
  municipal: "Municipio",
  comunal: "Comuna",
  nacional: "Nación",
  desconocido: "Sin nivel",
}
