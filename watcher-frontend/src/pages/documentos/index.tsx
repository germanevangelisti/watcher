import { useRef } from "react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Upload, CalendarDays, Database, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { useRouter } from "@tanstack/react-router"
import { BoletinCalendar } from "@/components/features/boletin-calendar"
import { FuentesDatoPanel } from "@/components/features/fuentes-dato-panel"
import { useUploadFiles } from "@/lib/api/hooks/use-upload"
import { usePipelineProcessOne } from "@/lib/api/hooks/use-pipeline"

function errMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}

export function DocumentosHub() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const router = useRouter()
  const uploadFiles = useUploadFiles()
  const processOne = usePipelineProcessOne()

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files
    if (!selected || selected.length === 0) return
    try {
      // Los N archivos van en un solo request: el endpoint acepta hasta 50 y
      // deduplica por hash dentro del lote.
      const result = await uploadFiles.mutateAsync(Array.from(selected))

      const rechazados = result.results.filter((r) => r.status === "failed")
      const subidos = result.results.filter((r) => r.status === "uploaded")
      const duplicados = result.results.filter((r) => r.status === "duplicate")

      if (rechazados.length > 0) {
        // El error se muestra, no se traga: antes iba a la consola y el botón
        // parecía no hacer nada.
        toast.error(
          rechazados.length === 1
            ? "El archivo fue rechazado"
            : `${rechazados.length} archivos fueron rechazados`,
          { description: rechazados.map((r) => `${r.filename}: ${r.error}`).join(" · ") },
        )
      }

      if (subidos.length === 0) {
        if (duplicados.length > 0) {
          toast.info("Ya estaba en el sistema", {
            description: duplicados.map((r) => `${r.filename} (igual a ${r.duplicate_of})`).join(" · "),
          })
        }
        return
      }

      // El PDF subido queda `pending` y sólo se analiza si alguien dispara el
      // pipeline.  Lo disparamos acá: un upload que no se procesa nunca no
      // aparece en el calendario (el nombre de archivo del BO no siempre tiene
      // el formato `YYYYMMDD_N_Secc.pdf` que el calendario necesita), así que
      // sin esto el botón seguía siendo un viaje de ida a ningún lado.
      const ids = subidos
        .map((r) => r.boletin_id)
        .filter((id): id is number => typeof id === "number")

      for (const id of ids) {
        processOne.mutate({ boletinId: id })
      }

      toast.success(
        ids.length === 1 ? "PDF subido — procesando" : `${ids.length} PDFs subidos — procesando`,
        {
          description: duplicados.length > 0 ? `${duplicados.length} duplicado(s) ignorado(s)` : undefined,
        },
      )

      // Con un solo archivo llevamos al documento, que es donde el usuario
      // quiere terminar.  Con varios no elegimos: serían análisis distintos.
      if (ids.length === 1) {
        router.navigate({ to: "/documentos/$id", params: { id: String(ids[0]) } })
      }
    } catch (err) {
      toast.error("No se pudieron subir los archivos", { description: errMessage(err) })
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Documentos</h1>
          <p className="text-muted-foreground mt-1">
            Boletines oficiales por jurisdicción y fuentes de datos públicos
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
            variant="outline"
            className="gap-2"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadFiles.isPending}
          >
            {uploadFiles.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            {uploadFiles.isPending ? "Subiendo..." : "Cargar PDF"}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="boletines">
        <TabsList>
          <TabsTrigger value="boletines" className="gap-2">
            <CalendarDays className="h-4 w-4" />
            Boletines
          </TabsTrigger>
          <TabsTrigger value="fuentes" className="gap-2">
            <Database className="h-4 w-4" />
            Fuentes de Datos
          </TabsTrigger>
        </TabsList>

        <TabsContent value="boletines" className="mt-6">
          <BoletinCalendar jurisdiccionId={1} />
        </TabsContent>

        <TabsContent value="fuentes" className="mt-6">
          <FuentesDatoPanel />
        </TabsContent>
      </Tabs>
    </div>
  )
}
