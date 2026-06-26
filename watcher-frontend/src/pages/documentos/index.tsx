import { useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Upload, CalendarDays, Database } from "lucide-react"
import { apiClient } from "@/lib/api/client"
import { BoletinCalendar } from "@/components/features/boletin-calendar"
import { FuentesDatoPanel } from "@/components/features/fuentes-dato-panel"

export function DocumentosHub() {
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
            disabled={uploading}
          >
            <Upload className="h-4 w-4" />
            {uploading ? "Subiendo..." : "Cargar PDF"}
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
