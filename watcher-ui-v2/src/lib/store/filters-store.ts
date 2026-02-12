import { create } from "zustand"
import { persist } from "zustand/middleware"

interface FiltersState {
  // Boletines filters
  boletinesFilters: {
    year?: number
    month?: number
    section?: string
    processed?: boolean
    search?: string
  }
  // Alertas filters
  alertasFilters: {
    nivel_severidad?: string
    estado?: string
    tipo_alerta?: string
    search?: string
  }
  // Search filters
  searchFilters: {
    technique?: "semantic" | "keyword" | "hybrid"
    maxResults?: number
    rerank?: boolean
  }
  // Actions
  setBoletinesFilters: (filters: Partial<FiltersState["boletinesFilters"]>) => void
  resetBoletinesFilters: () => void
  setAlertasFilters: (filters: Partial<FiltersState["alertasFilters"]>) => void
  resetAlertasFilters: () => void
  setSearchFilters: (filters: Partial<FiltersState["searchFilters"]>) => void
  resetSearchFilters: () => void
}

const defaultBoletinesFilters = {
  year: undefined,
  month: undefined,
  section: undefined,
  processed: undefined,
  search: "",
}

const defaultAlertasFilters = {
  nivel_severidad: undefined,
  estado: undefined,
  tipo_alerta: undefined,
  search: "",
}

const defaultSearchFilters = {
  technique: "semantic" as const,
  maxResults: 10,
  rerank: false,
}

export const useFiltersStore = create<FiltersState>()(
  persist(
    (set) => ({
      boletinesFilters: defaultBoletinesFilters,
      alertasFilters: defaultAlertasFilters,
      searchFilters: defaultSearchFilters,

      setBoletinesFilters: (filters) =>
        set((state) => ({
          boletinesFilters: { ...state.boletinesFilters, ...filters },
        })),

      resetBoletinesFilters: () =>
        set({ boletinesFilters: defaultBoletinesFilters }),

      setAlertasFilters: (filters) =>
        set((state) => ({
          alertasFilters: { ...state.alertasFilters, ...filters },
        })),

      resetAlertasFilters: () =>
        set({ alertasFilters: defaultAlertasFilters }),

      setSearchFilters: (filters) =>
        set((state) => ({
          searchFilters: { ...state.searchFilters, ...filters },
        })),

      resetSearchFilters: () =>
        set({ searchFilters: defaultSearchFilters }),
    }),
    {
      name: "watcher-filters-store",
    }
  )
)
