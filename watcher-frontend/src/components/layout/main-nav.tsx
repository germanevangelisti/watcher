import { Home, FileText, Brain, BarChart3, Workflow } from "lucide-react"
import { cn } from "@/lib/utils"

interface MainNavProps {
  currentPath?: string
  onNavigate?: (path: string) => void
}

const navItems = [
  {
    title: "Dashboard",
    href: "/",
    icon: Home,
  },
  {
    title: "Documentos",
    href: "/documentos",
    icon: FileText,
  },
  {
    title: "Conocimiento",
    href: "/conocimiento",
    icon: Brain,
  },
  {
    title: "Pipeline",
    href: "/pipeline",
    icon: Workflow,
  },
  {
    title: "Análisis",
    href: "/analisis",
    icon: BarChart3,
  },
]

export function MainNav({ currentPath = "/", onNavigate }: MainNavProps) {
  return (
    <nav className="space-y-1 px-2 py-4">
      {navItems.map((item) => {
        const Icon = item.icon
        const isActive = item.href === "/"
          ? currentPath === "/"
          : currentPath.startsWith(item.href)
        
        return (
          <button
            key={item.href}
            onClick={() => onNavigate?.(item.href)}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors",
              isActive
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )}
          >
            <Icon className="h-5 w-5 shrink-0" />
            <span>{item.title}</span>
          </button>
        )
      })}
    </nav>
  )
}
