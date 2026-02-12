import { useState, useRef } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useBoletines } from "@/lib/api/hooks/use-boletines"
import { BoletinCard } from "@/components/features/boletin-card"
import { BoletinFilters } from "@/components/features/boletin-filters"
import { PipelineControls } from "@/components/features/pipeline-controls"
import { SyncPanel } from "@/components/features/sync-panel"
import { FileText, Upload, AlertCircle, ChevronLeft, ChevronRight } from "lucide-react"
import { apiClient } from "@/lib/api/client"
import { useRouter } from "@tanstack/react-router"
import type { BoletinesFilters } from "@/types"

const PAGE_SIZE = 12

export function DocumentosHub() {
  const router = useRouter()
  const [filters, setFilters] = useState<BoletinesFilters>({
    limit: PAGE_SIZE,
    skip: 0,
    has_file: true,  // Only show documents with files on disk
  })

  const { data, isLoading, error } = useBoletines(filters)

  const currentPage = Math.floor((filters.skip || 0) / PAGE_SIZE) + 1
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  const handlePageChange = (page: number) => {
    setFilters((prev) => ({
      ...prev,
      skip: (page - 1) * PAGE_SIZE,
    }))
  }

  const handleFiltersChange = (newFilters: Omit<BoletinesFilters, 'limit' | 'skip'>) => {
    setFilters({
      ...newFilters,
      has_file: newFilters.has_file ?? true,  // Default to showing only files on disk
      limit: PAGE_SIZE,
      skip: 0, // Reset to first page when filters change
    })
  }

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploading(true)
    try {
      for (const file of Array.from(files)) {
        const formData = new FormData()
        formData.append("file", file)
        await apiClient.post("/upload/pdf", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        })
      }
      // Refresh boletines list
      setFilters((prev) => ({ ...prev }))
    } catch (err) {
      console.error("Upload error:", err)
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Documentos</h1>
          <p className="text-muted-foreground mt-2">
            Gestion de boletines oficiales y pipeline de procesamiento
          </p>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            className="hidden"
            onChange={handleUpload}
          />
          <Button
            className="gap-2"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <Upload className="h-4 w-4" />
            {uploading ? "Subiendo..." : "Cargar PDFs"}
          </Button>
        </div>
      </div>

      {/* Pipeline Controls */}
      <PipelineControls />

      {/* Sync Panel */}
      <SyncPanel />

      {/* Stats Summary */}
      {!error && !isLoading && data && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Total Documentos
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{data.total}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Página Actual</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {currentPage} / {totalPages}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Mostrando</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{data.boletines?.length ?? 0} docs</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <BoletinFilters
        filters={filters}
        onFiltersChange={handleFiltersChange}
      />

      {/* Error State */}
      {error && (
        <Card className="border-danger bg-danger/5">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-danger" />
              <CardTitle className="text-danger">Error al cargar documentos</CardTitle>
            </div>
            <CardDescription>
              No se pudieron cargar los documentos. Verifica la conexión con el backend.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-1/2 mt-2" />
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Documents Grid */}
      {!isLoading && !error && data && data.boletines && (
        <>
          {data.boletines.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FileText className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No se encontraron documentos</h3>
                <p className="text-sm text-muted-foreground">
                  Intenta ajustar los filtros o carga nuevos documentos
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {data.boletines.map((boletin) => (
                <BoletinCard
                  key={boletin.id}
                  boletin={boletin}
                  onView={(id) => router.navigate({ to: "/documentos/$id", params: { id: String(id) } })}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Mostrando {((currentPage - 1) * PAGE_SIZE) + 1} - {Math.min(currentPage * PAGE_SIZE, data.total)} de {data.total} documentos
              </p>
              
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                  Anterior
                </Button>
                
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum: number
                    if (totalPages <= 5) {
                      pageNum = i + 1
                    } else if (currentPage <= 3) {
                      pageNum = i + 1
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i
                    } else {
                      pageNum = currentPage - 2 + i
                    }

                    return (
                      <Button
                        key={pageNum}
                        variant={currentPage === pageNum ? "default" : "outline"}
                        size="sm"
                        onClick={() => handlePageChange(pageNum)}
                        className="w-10"
                      >
                        {pageNum}
                      </Button>
                    )
                  })}
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  Siguiente
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
