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

export function useTriggerFromDate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload: TriggerFromDatePayload) =>
      apiClient.post("/pipeline/trigger-from-date", payload).then((r) => r.data),
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
