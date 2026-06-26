import { useRef, useState } from "react"
import { Pencil, Check, X, Plus, ExternalLink, Newspaper, DollarSign, BarChart3, Upload, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  useFuentesDato,
  useCreateFuenteDato,
  useUpdateFuenteDato,
  useUploadFuenteDato,
} from "@/lib/api/hooks/use-fuentes-dato"
import { useJurisdicciones } from "@/lib/api/hooks/use-jurisdicciones"
import type { FuenteDato, TipoFuenteDato, JurisdiccionSimple } from "@/types"

// ─── Config por tipo ──────────────────────────────────────────────────────────

const TIPO_CONFIG: Record<TipoFuenteDato, { label: string; icon: React.ReactNode; placeholder: string }> = {
  boletin_diario: {
    label: "Boletín Oficial (diario)",
    icon: <Newspaper className="h-4 w-4 text-blue-500" />,
    placeholder: "https://boletinoficial.xxx.gov.ar/…/{year}/{month}/…",
  },
  presupuesto_anual: {
    label: "Presupuesto Anual",
    icon: <DollarSign className="h-4 w-4 text-green-500" />,
    placeholder: "https://…/presupuesto/{year}/…",
  },
  ejecucion_trimestral: {
    label: "Ejecución Trimestral",
    icon: <BarChart3 className="h-4 w-4 text-orange-500" />,
    placeholder: "https://…/ejecucion/{year}/trimestre/{quarter}/…",
  },
}

const TIPOS_ORDEN: TipoFuenteDato[] = ["boletin_diario", "presupuesto_anual", "ejecucion_trimestral"]

// ─── Fila de fuente editable ──────────────────────────────────────────────────

interface FuenteRowProps {
  tipo: TipoFuenteDato
  fuente: FuenteDato | undefined
  jurisdiccionId: number
}

function FuenteRow({ tipo, fuente, jurisdiccionId }: FuenteRowProps) {
  const cfg = TIPO_CONFIG[tipo]
  const updateMutation = useUpdateFuenteDato()
  const createMutation = useCreateFuenteDato()
  const uploadMutation = useUploadFuenteDato()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [editing, setEditing] = useState(false)
  const [url, setUrl] = useState(fuente?.url_template ?? "")
  const [activa, setActiva] = useState(fuente?.activa ?? true)
  const [uploadedName, setUploadedName] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !fuente) return
    setUploadError(null)
    try {
      const result = await uploadMutation.mutateAsync({ id: fuente.id, file })
      setUploadedName(result.filename)
    } catch {
      setUploadError("Error al subir el archivo.")
    } finally {
      e.target.value = ""
    }
  }

  const handleSave = async () => {
    if (fuente) {
      await updateMutation.mutateAsync({ id: fuente.id, url_template: url, activa })
    } else {
      await createMutation.mutateAsync({
        jurisdiccion_id: jurisdiccionId,
        tipo,
        nombre: cfg.label,
        url_template: url || undefined,
        activa,
      })
    }
    setEditing(false)
  }

  const handleCancel = () => {
    setUrl(fuente?.url_template ?? "")
    setActiva(fuente?.activa ?? true)
    setEditing(false)
  }

  const isSaving = updateMutation.isPending || createMutation.isPending

  return (
    <div className="space-y-2 py-3 border-b last:border-b-0">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {cfg.icon}
          <span className="text-sm font-medium">{cfg.label}</span>
          {fuente && (
            <Switch
              checked={activa}
              onCheckedChange={(v) => {
                setActiva(v)
                if (fuente) updateMutation.mutate({ id: fuente.id, activa: v })
              }}
              disabled={isSaving}
            />
          )}
        </div>
        <div className="flex items-center gap-1">
          {fuente?.url_template && !editing && (
            <a
              href={fuente.url_template.replace(/\{[^}]+\}/g, "…")}
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground"
              title="Abrir URL de referencia"
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
          {/* Upload button — only for non-boletin_diario when fuente exists */}
          {tipo !== "boletin_diario" && fuente && !editing && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={handleFileChange}
              />
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-2"
                title="Cargar archivo PDF"
                disabled={uploadMutation.isPending}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploadMutation.isPending
                  ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  : <Upload className="h-3.5 w-3.5" />
                }
              </Button>
            </>
          )}
          {editing ? (
            <>
              <Button size="sm" variant="ghost" className="h-7 px-2" onClick={handleSave} disabled={isSaving}>
                <Check className="h-3.5 w-3.5 text-green-600" />
              </Button>
              <Button size="sm" variant="ghost" className="h-7 px-2" onClick={handleCancel} disabled={isSaving}>
                <X className="h-3.5 w-3.5 text-muted-foreground" />
              </Button>
            </>
          ) : (
            <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => setEditing(true)}>
              {fuente ? <Pencil className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
            </Button>
          )}
        </div>
      </div>

      {editing ? (
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">URL o template</Label>
          <Input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder={cfg.placeholder}
            className="text-xs h-8 font-mono"
          />
          <p className="text-xs text-muted-foreground">
            Variables disponibles: {"{year}"}, {"{month}"}, {"{day}"}, {"{section}"}
          </p>
        </div>
      ) : (
        <>
          <div className="text-xs text-muted-foreground font-mono truncate">
            {fuente?.url_template ? (
              <span className="opacity-80">{fuente.url_template}</span>
            ) : (
              <span className="italic">No configurado</span>
            )}
          </div>
          {uploadedName && (
            <p className="text-xs text-green-600 mt-0.5">Subido: {uploadedName}</p>
          )}
          {uploadError && (
            <p className="text-xs text-destructive mt-0.5">{uploadError}</p>
          )}
        </>
      )}
    </div>
  )
}

// ─── Card por jurisdicción ────────────────────────────────────────────────────

interface JurisdiccionFuentesCardProps {
  jurisdiccionId: number
  jurisdiccionNombre: string
  fuentes: FuenteDato[]
}

function JurisdiccionFuentesCard({ jurisdiccionId, jurisdiccionNombre, fuentes }: JurisdiccionFuentesCardProps) {
  const fuentesByTipo = Object.fromEntries(fuentes.map((f) => [f.tipo, f])) as Record<TipoFuenteDato, FuenteDato | undefined>

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{jurisdiccionNombre}</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        {TIPOS_ORDEN.map((tipo) => (
          <FuenteRow
            key={tipo}
            tipo={tipo}
            fuente={fuentesByTipo[tipo]}
            jurisdiccionId={jurisdiccionId}
          />
        ))}
      </CardContent>
    </Card>
  )
}

// ─── Panel principal ──────────────────────────────────────────────────────────

export function FuentesDatoPanel() {
  const { data: fuentes, isLoading: loadingFuentes } = useFuentesDato()
  const { data: jurisdicciones, isLoading: loadingJ } = useJurisdicciones()

  const isLoading = loadingFuentes || loadingJ

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2].map((i) => (
          <Card key={i}>
            <CardHeader><Skeleton className="h-5 w-48" /></CardHeader>
            <CardContent className="space-y-3">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  // Build: jurisdiccion_id → fuentes list
  const fuentesByJurisdiccion = new Map<number, FuenteDato[]>()
  for (const f of fuentes ?? []) {
    const arr = fuentesByJurisdiccion.get(f.jurisdiccion_id) ?? []
    arr.push(f)
    fuentesByJurisdiccion.set(f.jurisdiccion_id, arr)
  }

  // Show jurisdictions that already have ≥1 fuente configured
  // + any jurisdiction without fuentes is shown if it's PROVINCIAL type
  const jurisdiccionesConFuentes = (jurisdicciones ?? []).filter(
    (j: JurisdiccionSimple) =>
      fuentesByJurisdiccion.has(j.id) || j.tipo === "provincia"
  )

  if (jurisdiccionesConFuentes.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        No hay jurisdicciones configuradas. Primero registra una jurisdicción.
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Configurá las URLs de acceso a fuentes de datos públicos por jurisdicción.
        Las variables en URL templates se reemplazan automáticamente al momento del acceso.
      </p>
      {jurisdiccionesConFuentes.map((j: JurisdiccionSimple) => (
        <JurisdiccionFuentesCard
          key={j.id}
          jurisdiccionId={j.id}
          jurisdiccionNombre={j.nombre}
          fuentes={fuentesByJurisdiccion.get(j.id) ?? []}
        />
      ))}
    </div>
  )
}
