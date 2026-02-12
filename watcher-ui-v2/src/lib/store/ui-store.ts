import { create } from "zustand"
import { persist } from "zustand/middleware"

interface UIStore {
  sidebarOpen: boolean
  sidebarCollapsed: boolean
  theme: "dark" | "light" | "system"
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  toggleSidebarCollapsed: () => void
  setTheme: (theme: "dark" | "light" | "system") => void
}

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      sidebarCollapsed: false,
      theme: "dark",
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleSidebarCollapsed: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: "watcher-ui-store",
    }
  )
)
