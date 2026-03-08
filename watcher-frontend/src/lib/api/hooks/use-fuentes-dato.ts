import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import apiClient from "../client"
import type { FuenteDato, FuenteDatoCreateRequest, FuenteDatoUpdateRequest } from "@/types"

export function useFuentesDato(jurisdiccionId?: number) {
  return useQuery({
    queryKey: ["fuentes-dato", jurisdiccionId],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (jurisdiccionId !== undefined) {
        params.append("jurisdiccion_id", jurisdiccionId.toString())
      }
      const { data } = await apiClient.get<FuenteDato[]>(
        `/fuentes-dato/?${params.toString()}`
      )
      return data
    },
  })
}

export function useCreateFuenteDato() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: FuenteDatoCreateRequest) => {
      const { data } = await apiClient.post<FuenteDato>("/fuentes-dato", body)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fuentes-dato"] })
    },
  })
}

export function useUpdateFuenteDato() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...body }: { id: number } & FuenteDatoUpdateRequest) => {
      const { data } = await apiClient.put<FuenteDato>(`/fuentes-dato/${id}`, body)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fuentes-dato"] })
    },
  })
}

export function useDeleteFuenteDato() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/fuentes-dato/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fuentes-dato"] })
    },
  })
}

export function useUploadFuenteDato() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, file }: { id: number; file: File }) => {
      const form = new FormData()
      form.append("file", file)
      const { data } = await apiClient.post<{ boletin_id: number; filename: string; message: string }>(
        `/fuentes-dato/${id}/upload`,
        form,
        { headers: { "Content-Type": "multipart/form-data" } },
      )
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fuentes-dato"] })
    },
  })
}
