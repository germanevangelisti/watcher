import { useMutation, useQueryClient } from "@tanstack/react-query"
import apiClient from "../client"

interface TriggerFromDatePayload {
  jurisdiccion_id: number
  date: string    // "YYYYMMDD"
  section: string // "1" … "5"
}

interface TriggerMonthPayload {
  jurisdiccion_id: number
  year: number
  month: number
  sections?: string[]
}

interface TriggerDayPayload {
  jurisdiccion_id: number
  date: string
  sections: string[]
}

/**
 * Lo que contesta `POST /pipeline/trigger-from-date`.
 *
 * `already_completed` es la parte importante: el endpoint busca la fila por
 * filename y, si ya está `completed`, no reprocesa nada y devuelve
 * `already_completed: true` con el `boletin_id` existente. Ese `boletin_id` es
 * la única forma que tiene el frontend de llegar a un documento que el
 * calendario no está mostrando.
 */
export interface TriggerFromDateResponse {
  success: boolean
  boletin_id: number
  session_id?: string
  filename: string
  source_url: string
  message: string
  already_completed?: boolean
}

export function useTriggerFromDate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: TriggerFromDatePayload) =>
      apiClient
        .post<TriggerFromDateResponse>("/pipeline/trigger-from-date", payload)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["boletin-calendar"] })
    },
  })
}

export function useTriggerDay() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ jurisdiccion_id, date, sections }: TriggerDayPayload) =>
      Promise.all(
        sections.map((section) =>
          apiClient
            .post<TriggerFromDateResponse>("/pipeline/trigger-from-date", {
              jurisdiccion_id,
              date,
              section,
            })
            .then((r) => r.data)
        )
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["boletin-calendar"] })
    },
  })
}

export function useTriggerMonth() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: TriggerMonthPayload) =>
      apiClient.post("/pipeline/trigger-month", payload).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["boletin-calendar"] })
    },
  })
}
