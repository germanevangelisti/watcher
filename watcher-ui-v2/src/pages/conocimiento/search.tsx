import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { FadeTransition } from "@/components/ui/fade-transition"
import { useSearch } from "@/lib/api"
import { Search, Filter, X, ChevronDown, ExternalLink, FileText, Sparkles, Hash, Zap } from "lucide-react"
import { Link } from "@tanstack/react-router"
import type { SearchRequest, SearchResult } from "@/types"

export function SearchPage() {
  const [query, setQuery] = useState("")
  const [technique, setTechnique] = useState<"semantic" | "keyword" | "hybrid">("hybrid")
  const [showFilters, setShowFilters] = useState(false)
  const [topK, setTopK] = useState(10)
  const [rerank, setRerank] = useState(false)

  const searchMutation = useSearch()

  const handleSearch = () => {
    if (!query.trim()) return

    const request: SearchRequest = {
      query: query.trim(),
      top_k: topK,
      technique,
      rerank,
    }

    searchMutation.mutate(request)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSearch()
    }
  }

  const getTechniqueIcon = (tech: string) => {
    switch (tech) {
      case "semantic":
        return <Sparkles className="h-3 w-3" />
      case "keyword":
        return <Hash className="h-3 w-3" />
      case "hybrid":
        return <Zap className="h-3 w-3" />
      default:
        return null
    }
  }

  const getTechniqueColor = (tech: string) => {
    switch (tech) {
      case "semantic":
        return "bg-purple-500/10 text-purple-500 border-purple-500/20"
      case "keyword":
        return "bg-blue-500/10 text-blue-500 border-blue-500/20"
      case "hybrid":
        return "bg-green-500/10 text-green-500 border-green-500/20"
      default:
        return ""
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Búsqueda Semántica</h1>
        <p className="text-muted-foreground mt-2">
          Busca información en documentos usando lenguaje natural
        </p>
      </div>

      {/* Search Bar */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Buscador
          </CardTitle>
          <CardDescription>
            Ingresa tu consulta y selecciona la técnica de búsqueda
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Main Search Input */}
          <div className="flex gap-2">
            <Input
              placeholder="Ej: licitaciones públicas en Córdoba 2025..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              className="flex-1"
            />
            <Button onClick={handleSearch} disabled={!query.trim() || searchMutation.isPending}>
              {searchMutation.isPending ? "Buscando..." : "Buscar"}
            </Button>
          </div>

          {/* Technique Selector */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Técnica:</span>
            <div className="flex gap-2">
              <Button
                variant={technique === "semantic" ? "default" : "outline"}
                size="sm"
                onClick={() => setTechnique("semantic")}
                className="gap-1"
              >
                <Sparkles className="h-3 w-3" />
                Semántica
              </Button>
              <Button
                variant={technique === "keyword" ? "default" : "outline"}
                size="sm"
                onClick={() => setTechnique("keyword")}
                className="gap-1"
              >
                <Hash className="h-3 w-3" />
                Keywords
              </Button>
              <Button
                variant={technique === "hybrid" ? "default" : "outline"}
                size="sm"
                onClick={() => setTechnique("hybrid")}
                className="gap-1"
              >
                <Zap className="h-3 w-3" />
                Híbrida
              </Button>
            </div>
          </div>

          {/* Advanced Filters Toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className="gap-2"
          >
            <Filter className="h-4 w-4" />
            Filtros avanzados
            <ChevronDown className={`h-4 w-4 transition-transform ${showFilters ? "rotate-180" : ""}`} />
          </Button>

          {/* Advanced Filters */}
          {showFilters && (
            <div className="border-t pt-4 space-y-3">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Resultados máximos</label>
                  <Input
                    type="number"
                    min="1"
                    max="50"
                    value={topK}
                    onChange={(e) => setTopK(parseInt(e.target.value) || 10)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium flex items-center gap-2">
                    Re-ranking
                    <Badge variant="secondary" className="text-xs">Experimental</Badge>
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={rerank}
                      onChange={(e) => setRerank(e.target.checked)}
                      className="h-4 w-4"
                    />
                    <span className="text-sm text-muted-foreground">
                      Mejorar relevancia con re-ranking
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results with smooth transitions */}
      <FadeTransition
        isLoading={searchMutation.isPending}
        skeleton={
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-32" />
            </CardHeader>
            <CardContent className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ))}
            </CardContent>
          </Card>
        }
      >
        {searchMutation.isError && (
        <Card className="border-danger">
          <CardHeader>
            <CardTitle className="text-danger">Error en la búsqueda</CardTitle>
            <CardDescription>
              {searchMutation.error instanceof Error
                ? searchMutation.error.message
                : "No se pudo completar la búsqueda"}
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {searchMutation.isSuccess && searchMutation.data && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  Resultados
                  <Badge variant="secondary">{searchMutation.data.total_results}</Badge>
                </CardTitle>
                <CardDescription>
                  {searchMutation.data.technique && (
                    <>
                      Búsqueda con técnica{" "}
                      <Badge className={`gap-1 ${getTechniqueColor(searchMutation.data.technique)}`}>
                        {getTechniqueIcon(searchMutation.data.technique)}
                        {searchMutation.data.technique}
                      </Badge>
                    </>
                  )}
                  {searchMutation.data.reranked && (
                    <Badge variant="outline" className="ml-2">Re-ranked</Badge>
                  )}
                  {" • "}
                  {searchMutation.data.execution_time_ms.toFixed(0)}ms
                </CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => searchMutation.reset()}
                className="gap-2"
              >
                <X className="h-4 w-4" />
                Limpiar
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {searchMutation.data.results.length === 0 ? (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-lg font-medium">No se encontraron resultados</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Intenta con otros términos de búsqueda o cambia la técnica
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {searchMutation.data.results.map((result: SearchResult, idx: number) => (
                  <div
                    key={idx}
                    className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="font-mono text-xs">
                            Score: {result.score.toFixed(3)}
                          </Badge>
                          {result.metadata?.document_id && (
                            <Badge variant="secondary" className="text-xs">
                              Doc #{result.metadata.document_id}
                            </Badge>
                          )}
                          {result.metadata?.chunk_id && (
                            <Badge variant="secondary" className="text-xs">
                              Chunk #{result.metadata.chunk_id}
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm leading-relaxed">{result.document}</p>
                        {result.metadata && (
                          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                            {result.metadata.filename && (
                              <span>📄 {result.metadata.filename}</span>
                            )}
                            {result.metadata.section && (
                              <span>📑 Sección {result.metadata.section}</span>
                            )}
                            {result.metadata.date && (
                              <span>📅 {result.metadata.date}</span>
                            )}
                          </div>
                        )}
                      </div>
                      {result.metadata?.document_id && (
                        <Link to="/documentos/$id" params={{ id: result.metadata.document_id }}>
                          <Button variant="ghost" size="sm" className="gap-2">
                            <ExternalLink className="h-4 w-4" />
                            Ver documento
                          </Button>
                        </Link>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        )}
      </FadeTransition>
    </div>
  )
}
