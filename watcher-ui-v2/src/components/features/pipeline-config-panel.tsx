/**
 * PipelineConfigPanel - Full pipeline configuration dialog/sheet.
 * Allows users to configure each pipeline stage before execution.
 */

import { useState, useEffect } from "react"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  DEFAULT_PIPELINE_CONFIG,
  type PipelineConfigState,
} from "@/lib/store/pipeline-store"
import { usePipelineDefaults } from "@/lib/api/hooks/use-pipeline"
import {
  FileSearch,
  Sparkles,
  Layers,
  Database,
  Eraser,
  RotateCcw,
  Play,
} from "lucide-react"

interface PipelineConfigPanelProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onExecute: (config: PipelineConfigState) => void
  title?: string
}

export function PipelineConfigPanel({
  open,
  onOpenChange,
  onExecute,
  title = "Configuracion del Pipeline",
}: PipelineConfigPanelProps) {
  const { data: defaults } = usePipelineDefaults()
  const [config, setConfig] = useState<PipelineConfigState>(
    defaults || DEFAULT_PIPELINE_CONFIG
  )

  // Sync defaults when loaded
  useEffect(() => {
    if (defaults) {
      setConfig(defaults)
    }
  }, [defaults])

  const resetDefaults = () => {
    setConfig(defaults || DEFAULT_PIPELINE_CONFIG)
  }

  const handleExecute = () => {
    onExecute(config)
    onOpenChange(false)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[440px] sm:w-[540px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>
            Configura las opciones tecnicas de cada fase del procesamiento.
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-6 py-6">
          {/* 1. EXTRACTION */}
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <FileSearch className="h-4 w-4 text-blue-400" />
              <h3 className="font-semibold text-sm">1. Extraccion</h3>
            </div>
            <div className="pl-6 space-y-2">
              <Label className="text-xs text-muted-foreground">
                Metodo de extraccion de PDF
              </Label>
              <div className="flex gap-2">
                {["pdfplumber", "pypdf2"].map((method) => (
                  <Badge
                    key={method}
                    variant={
                      config.extraction.extractor === method
                        ? "default"
                        : "outline"
                    }
                    className="cursor-pointer"
                    onClick={() =>
                      setConfig((c) => ({
                        ...c,
                        extraction: { ...c.extraction, extractor: method },
                      }))
                    }
                  >
                    {method}
                  </Badge>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                pdfplumber: mejor calidad, mas lento. pypdf2: mas rapido.
              </p>
            </div>
          </section>

          {/* 2. CLEANING */}
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <Eraser className="h-4 w-4 text-cyan-400" />
              <h3 className="font-semibold text-sm">2. Limpieza</h3>
              <div className="ml-auto flex items-center gap-2">
                <Label className="text-xs">Habilitada</Label>
                <Switch
                  checked={config.cleaning.enabled}
                  onCheckedChange={(v) =>
                    setConfig((c) => ({
                      ...c,
                      cleaning: { ...c.cleaning, enabled: v },
                    }))
                  }
                />
              </div>
            </div>
            {config.cleaning.enabled && (
              <div className="pl-6 grid grid-cols-2 gap-3">
                {(
                  [
                    ["fix_encoding", "Fix encoding (ftfy)"],
                    ["normalize_unicode", "Normalizar unicode"],
                    ["normalize_whitespace", "Normalizar whitespace"],
                    ["remove_artifacts", "Remover artefactos PDF"],
                    ["normalize_legal_text", "Normalizar texto legal"],
                  ] as const
                ).map(([key, label]) => (
                  <div key={key} className="flex items-center gap-2">
                    <Switch
                      checked={
                        config.cleaning[key as keyof typeof config.cleaning] as boolean
                      }
                      onCheckedChange={(v) =>
                        setConfig((c) => ({
                          ...c,
                          cleaning: { ...c.cleaning, [key]: v },
                        }))
                      }
                    />
                    <Label className="text-xs">{label}</Label>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* 3. CHUNKING */}
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-yellow-400" />
              <h3 className="font-semibold text-sm">3. Chunking</h3>
            </div>
            <div className="pl-6 space-y-4">
              {/* Chunk Size */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Chunk size</Label>
                  <span className="text-xs text-muted-foreground font-mono">
                    {config.chunking.chunk_size} chars
                  </span>
                </div>
                <Slider
                  value={[config.chunking.chunk_size]}
                  min={100}
                  max={5000}
                  step={100}
                  onValueChange={([v]) =>
                    setConfig((c) => ({
                      ...c,
                      chunking: { ...c.chunking, chunk_size: v },
                    }))
                  }
                />
              </div>

              {/* Overlap */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Overlap</Label>
                  <span className="text-xs text-muted-foreground font-mono">
                    {config.chunking.chunk_overlap} chars
                  </span>
                </div>
                <Slider
                  value={[config.chunking.chunk_overlap]}
                  min={0}
                  max={1000}
                  step={50}
                  onValueChange={([v]) =>
                    setConfig((c) => ({
                      ...c,
                      chunking: { ...c.chunking, chunk_overlap: v },
                    }))
                  }
                />
              </div>

              {/* Min Chunk Size */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs">Min chunk size</Label>
                  <span className="text-xs text-muted-foreground font-mono">
                    {config.chunking.min_chunk_size} chars
                  </span>
                </div>
                <Slider
                  value={[config.chunking.min_chunk_size]}
                  min={50}
                  max={500}
                  step={25}
                  onValueChange={([v]) =>
                    setConfig((c) => ({
                      ...c,
                      chunking: { ...c.chunking, min_chunk_size: v },
                    }))
                  }
                />
              </div>
            </div>
          </section>

          {/* 4. ENRICHMENT */}
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-purple-400" />
              <h3 className="font-semibold text-sm">4. Enriquecimiento</h3>
              <div className="ml-auto flex items-center gap-2">
                <Label className="text-xs">Habilitado</Label>
                <Switch
                  checked={config.enrichment.enabled}
                  onCheckedChange={(v) =>
                    setConfig((c) => ({
                      ...c,
                      enrichment: { ...c.enrichment, enabled: v },
                    }))
                  }
                />
              </div>
            </div>
            {config.enrichment.enabled && (
              <div className="pl-6 grid grid-cols-2 gap-3">
                {(
                  [
                    ["detect_section_type", "Tipo de seccion"],
                    ["detect_amounts", "Detectar montos"],
                    ["detect_tables", "Detectar tablas"],
                    ["extract_entities", "Extraer entidades"],
                  ] as const
                ).map(([key, label]) => (
                  <div key={key} className="flex items-center gap-2">
                    <Switch
                      checked={
                        config.enrichment[
                          key as keyof typeof config.enrichment
                        ] as boolean
                      }
                      onCheckedChange={(v) =>
                        setConfig((c) => ({
                          ...c,
                          enrichment: { ...c.enrichment, [key]: v },
                        }))
                      }
                    />
                    <Label className="text-xs">{label}</Label>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* 5. INDEXING */}
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-orange-400" />
              <h3 className="font-semibold text-sm">5. Indexacion</h3>
            </div>
            <div className="pl-6 space-y-3">
              <div className="grid grid-cols-1 gap-3">
                {(
                  [
                    ["use_sqlite", "SQLite (chunk records)"],
                    ["use_fts5", "FTS5 (full-text search)"],
                    ["use_chromadb", "ChromaDB (vector embeddings)"],
                  ] as const
                ).map(([key, label]) => (
                  <div key={key} className="flex items-center gap-2">
                    <Switch
                      checked={
                        config.indexing[
                          key as keyof typeof config.indexing
                        ] as boolean
                      }
                      onCheckedChange={(v) =>
                        setConfig((c) => ({
                          ...c,
                          indexing: { ...c.indexing, [key]: v },
                        }))
                      }
                    />
                    <Label className="text-xs">{label}</Label>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <Label className="text-xs text-muted-foreground">Modelo:</Label>
                <Badge variant="outline" className="text-xs">
                  {config.indexing.embedding_model}
                </Badge>
              </div>
            </div>
          </section>
        </div>

        <SheetFooter className="flex-row gap-2 pt-4 border-t">
          <Button variant="outline" size="sm" onClick={resetDefaults} className="gap-1">
            <RotateCcw className="h-3 w-3" />
            Defaults
          </Button>
          <div className="flex-1" />
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button size="sm" onClick={handleExecute} className="gap-1">
            <Play className="h-3 w-3" />
            Ejecutar Pipeline
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
