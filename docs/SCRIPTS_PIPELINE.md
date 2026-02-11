# Pipeline de Procesamiento de Boletines

## Flujo de Scripts

```
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE DE PROCESAMIENTO                    │
└─────────────────────────────────────────────────────────────────┘

    /boletines/*.pdf  (PDFs crudos)
            │
            │
            ▼
    ┌───────────────────────────┐
    │  1. register_boletines.py │  📝 REGISTRO
    └───────────────────────────┘
    • Escanea directorio /boletines
    • Registra PDFs en la BD (tabla: boletines)
    • Extrae metadata: fecha, sección, jurisdicción
    • Estado inicial: 'pending'
    • Marca jurisdiccion_id=1 (Córdoba)
            │
            │
            ▼
    ┌─────────────────────────────┐
    │ 2. extraer_texto_masivo.py  │  📄 EXTRACCIÓN DE TEXTO
    └─────────────────────────────┘
    • Lee boletines con status='pending'
    • Usa PyPDF2 para extraer texto
    • Guarda en: /data/processed/{filename}.txt
    • Actualiza estado: 'completed'
            │
            │
            ▼
    ┌────────────────────────────────┐
    │ 3. extraer_entidades_masivo.py │  🏢 EXTRACCIÓN DE ENTIDADES
    └────────────────────────────────┘
    • Lee boletines con status='completed'
    • Extrae entidades con regex:
      - Personas
      - Organismos
      - Empresas
      - Contratos
      - Montos
    • Detecta relaciones (contrata, designa, adjudica)
    • Guarda en: entidades_extraidas, menciones_entidades,
      relaciones_entidades
            │
            │
            ▼
    ┌───────────────────────────┐
    │ 4. indexar_embeddings.py  │  🔍 INDEXACIÓN VECTORIAL
    └───────────────────────────┘
    • Lee archivos de texto procesados
    • Genera embeddings con sentence-transformers
    • Indexa en ChromaDB (chunks de 512 tokens)
    • Metadata: fecha, sección, jurisdicción, filename
    • Habilita búsqueda semántica


┌─────────────────────────────────────────────────────────────────┐
│                       RESULTADO FINAL                           │
└─────────────────────────────────────────────────────────────────┘

    DATABASE (SQLite)
    ├── boletines (registros de PDFs)
    ├── entidades_extraidas (Knowledge Graph)
    ├── menciones_entidades (contexto)
    └── relaciones_entidades (vínculos)

    CHROMADB (Vector Store)
    └── watcher_documents (embeddings para búsqueda semántica)

    FILESYSTEM
    └── /data/processed/*.txt (texto extraído)
```

## Comandos de Uso

### 1. Registrar PDFs nuevos
```bash
python scripts/register_boletines.py
```

### 2. Extraer texto
```bash
# Todos los documentos pending
python scripts/extraer_texto_masivo.py

# Filtrado por fecha
python scripts/extraer_texto_masivo.py --year 2026 --month 02 --day 03
```

### 3. Extraer entidades
```bash
# Todos los documentos completed
python scripts/extraer_entidades_masivo.py

# Filtrado por fecha
python scripts/extraer_entidades_masivo.py --year 2026 --month 02 --day 03
```

### 4. Indexar embeddings
```bash
# Todos los documentos
python scripts/indexar_embeddings.py

# Filtrado por fecha
python scripts/indexar_embeddings.py --year 2026 --month 02 --day 03

# Forzar re-indexación
python scripts/indexar_embeddings.py --force
```

## Parámetros Comunes

| Parámetro | Descripción | Scripts que lo soportan |
|-----------|-------------|------------------------|
| `--year YYYY` | Filtrar por año | 2, 3, 4 |
| `--month MM` | Filtrar por mes | 2, 3, 4 |
| `--day DD` | Filtrar por día | 2, 3, 4 |
| `--limit N` | Límite de documentos | 2, 3 |
| `--batch-size N` | Tamaño de lote | 2, 3, 4 |
| `--force` | Forzar re-procesamiento | 4 |

## Estados de Boletín

```
pending   → texto sin extraer
completed → texto extraído, entidades pendientes
ready     → todo procesado
```

## Orden Recomendado

1. **Registro inicial** (una vez)
   ```bash
   python scripts/register_boletines.py
   ```

2. **Pipeline completo** (para nuevos documentos)
   ```bash
   python scripts/extraer_texto_masivo.py --year 2026
   python scripts/extraer_entidades_masivo.py --year 2026
   python scripts/indexar_embeddings.py --year 2026
   ```

3. **Re-procesamiento selectivo** (por fecha)
   ```bash
   python scripts/extraer_texto_masivo.py --year 2026 --month 02 --day 03
   python scripts/extraer_entidades_masivo.py --year 2026 --month 02 --day 03
   python scripts/indexar_embeddings.py --year 2026 --month 02 --day 03
   ```

## Verificación de Estado

Para ver cuántos boletines están en cada etapa:

```sql
-- En la BD SQLite
SELECT status, COUNT(*) FROM boletines GROUP BY status;
```

O usando Python:
```python
from app.db.session import AsyncSessionLocal
from app.db.models import Boletin
from sqlalchemy import select, func

async def check_status():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Boletin.status, func.count(Boletin.id))
            .group_by(Boletin.status)
        )
        for status, count in result:
            print(f"{status}: {count}")
```
