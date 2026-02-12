import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Filter, X } from "lucide-react"
import { useJurisdicciones } from "@/lib/api/hooks/use-jurisdicciones"
import type { BoletinesFilters } from "@/types"

interface BoletinFiltersProps {
  filters: BoletinesFilters
  onFiltersChange: (filters: BoletinesFilters) => void
}

const SECTIONS = ["1_Secc", "2_Secc", "3_Secc", "Especial"]
const YEARS = [2025, 2024, 2023, 2022]
const MONTHS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

export function BoletinFilters({ filters, onFiltersChange }: BoletinFiltersProps) {
  const { data: jurisdicciones } = useJurisdicciones()
  const hasFilters = filters.year || filters.month || filters.section || filters.processed !== undefined || filters.has_file !== undefined || filters.jurisdiccion_id !== undefined

  const handleClear = () => {
    onFiltersChange({})
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <h3 className="font-semibold">Filtros</h3>
            {hasFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClear}
                className="ml-auto h-8"
              >
                <X className="h-4 w-4 mr-1" />
                Limpiar
              </Button>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
            <div className="space-y-2">
              <label className="text-sm font-medium">Año</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={filters.year || ""}
                onChange={(e) =>
                  onFiltersChange({
                    ...filters,
                    year: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
              >
                <option value="">Todos</option>
                {YEARS.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Mes</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={filters.month || ""}
                onChange={(e) =>
                  onFiltersChange({
                    ...filters,
                    month: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
              >
                <option value="">Todos</option>
                {MONTHS.map((month) => (
                  <option key={month} value={month}>
                    {month}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Sección</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={filters.section || ""}
                onChange={(e) =>
                  onFiltersChange({
                    ...filters,
                    section: e.target.value || undefined,
                  })
                }
              >
                <option value="">Todas</option>
                {SECTIONS.map((section) => (
                  <option key={section} value={section}>
                    {section}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Estado</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={
                  filters.processed === undefined
                    ? ""
                    : filters.processed
                    ? "true"
                    : "false"
                }
                onChange={(e) =>
                  onFiltersChange({
                    ...filters,
                    processed:
                      e.target.value === ""
                        ? undefined
                        : e.target.value === "true",
                  })
                }
              >
                <option value="">Todos</option>
                <option value="true">Procesados</option>
                <option value="false">Pendientes</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Archivo</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={
                  filters.has_file === undefined
                    ? ""
                    : filters.has_file
                    ? "true"
                    : "false"
                }
                onChange={(e) =>
                  onFiltersChange({
                    ...filters,
                    has_file:
                      e.target.value === ""
                        ? undefined
                        : e.target.value === "true",
                  })
                }
              >
                <option value="">Todos</option>
                <option value="true">Con PDF</option>
                <option value="false">Sin PDF</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Jurisdicción</label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={filters.jurisdiccion_id ?? ""}
                onChange={(e) =>
                  onFiltersChange({
                    ...filters,
                    jurisdiccion_id: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
              >
                <option value="">Todas</option>
                {jurisdicciones?.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.nombre} ({j.tipo})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
