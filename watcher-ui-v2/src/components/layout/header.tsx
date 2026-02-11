import { Menu } from "lucide-react"
import { Button } from "@/components/ui/button"

interface HeaderProps {
  onMenuClick: () => void
}

export function Header({ onMenuClick }: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-4 gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={onMenuClick}
          className="lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </Button>

        <div className="flex items-center gap-2">
          <span className="font-bold text-lg">🧿 Watcher</span>
        </div>

        <div className="ml-auto flex items-center gap-4">
          <div className="text-sm text-muted-foreground hidden sm:block">
            MVP v1.1
          </div>
        </div>
      </div>
    </header>
  )
}
