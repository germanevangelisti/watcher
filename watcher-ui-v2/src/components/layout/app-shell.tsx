import { useState } from "react"
import { Header } from "./header"
import { MainNav } from "./main-nav"
import { cn } from "@/lib/utils"

interface AppShellProps {
  children: React.ReactNode
  currentPath?: string
  onNavigate?: (path: string) => void
}

export function AppShell({ children, currentPath, onNavigate }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-background">
      <Header onMenuClick={() => setSidebarOpen(!sidebarOpen)} />

      <div className="flex">
        {/* Sidebar */}
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-40 w-64 border-r border-border bg-card transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static",
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          )}
          style={{ top: "3.5rem" }}
        >
          <MainNav currentPath={currentPath} onNavigate={onNavigate} />
        </aside>

        {/* Overlay for mobile */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-30 bg-background/80 backdrop-blur-sm lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Main content */}
        <main className="flex-1 overflow-auto">
          <div className="container mx-auto p-6 max-w-7xl">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
