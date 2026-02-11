# 🏗️ Arquitectura de Almacenamiento para Boletines Oficiales

## 📊 Situación Actual

### Almacenamiento Local (Filesystem)
```
📁 Ubicación: /Users/germanevangelisti/watcher-agent/boletines
📈 Archivos actuales: 207 PDFs
💾 Espacio ocupado: 159 MB
📏 Tamaño promedio: 0.76 MB por archivo
```

### Base de Datos (SQLite/PostgreSQL)
La tabla `boletines` almacena solo **metadata**:
- ✅ `filename` (nombre del archivo)
- ✅ `date` (fecha YYYYMMDD)
- ✅ `section` (sección 1-5)
- ✅ `status` (pending, completed, failed)
- ❌ **NO almacena el PDF** (solo referencia)

---

## 📈 Proyecciones de Crecimiento

### Escenario Real
```
📅 Por año (250 días hábiles × 5 secciones):
   • Archivos: 1,250 PDFs
   • Espacio: ~950 MB (~0.9 GB)

📊 5 años:
   • Archivos: 6,250 PDFs
   • Espacio: ~4.6 GB

📊 10 años:
   • Archivos: 12,500 PDFs
   • Espacio: ~9.3 GB
```

**Conclusión**: El volumen es **manejable** incluso a largo plazo.

---

## 🎯 Opciones de Arquitectura

### **Opción 1: Filesystem Local** ⭐ RECOMENDADA

#### ✅ Pros
- **Simplicidad**: Sin complejidad adicional
- **Rendimiento**: Acceso directo a archivos
- **Costo**: $0 (usa infraestructura existente)
- **Velocidad**: Lectura/escritura inmediata
- **Debugging**: Fácil inspección manual de archivos
- **Backup**: Fácil con rsync/scripts simples
- **Escalabilidad**: Suficiente para 10+ años

#### ❌ Contras
- **Single point of failure**: Si se pierde el disco, se pierde todo
- **No compartido**: Difícil acceso desde múltiples servidores
- **Backup manual**: Requiere configuración de respaldos
- **Sin versionado**: Sobreescribe archivos si se re-descarga

#### 🏗️ Arquitectura
```
┌─────────────────────────────────────────┐
│         FastAPI Backend                 │
│  ┌───────────────────────────────────┐  │
│  │  Downloader Service               │  │
│  │  ├─ Descarga PDFs                 │  │
│  │  └─ Guarda en filesystem          │  │
│  └───────────────────────────────────┘  │
│              ↓                          │
│  ┌───────────────────────────────────┐  │
│  │  /boletines/                      │  │
│  │  ├─ 20250801_1_Secc.pdf           │  │
│  │  ├─ 20250801_2_Secc.pdf           │  │
│  │  └─ ...                            │  │
│  └───────────────────────────────────┘  │
│              ↓                          │
│  ┌───────────────────────────────────┐  │
│  │  PostgreSQL/SQLite                │  │
│  │  └─ Metadata (filename, status)   │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

#### 💡 Mejoras Recomendadas
```python
# 1. Estructura organizada por año/mes
BOLETINES_DIR = Path("/data/boletines")
estructura:
  /data/boletines/
    ├── 2025/
    │   ├── 08/
    │   │   ├── 20250801_1_Secc.pdf
    │   │   └── ...
    │   └── 09/
    └── 2026/

# 2. Backup automático (cron diario)
rsync -avz /data/boletines/ /backup/boletines/

# 3. Compresión opcional (reduce 30-50%)
gzip /data/boletines/2024/**/*.pdf
```

---

### **Opción 2: Base de Datos (BYTEA/BLOB)** ⚠️ NO RECOMENDADA

#### ✅ Pros
- **Centralizado**: Todo en un solo lugar
- **Transaccional**: Atomicidad garantizada
- **Backup integrado**: Con pg_dump
- **Versionado**: Posible con columnas adicionales
- **Permisos**: Control granular por SQL

#### ❌ Contras
- **Rendimiento**: Lento para archivos grandes
- **Tamaño DB**: Crece exponencialmente
- **Backup pesado**: Dumps muy grandes
- **Memoria**: Carga archivos completos en RAM
- **Complejidad**: Queries más lentos
- **Costo**: Bases de datos grandes son caras

#### 📊 Impacto en DB
```sql
-- Tabla con PDFs (NO RECOMENDADO)
CREATE TABLE boletines (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255),
    pdf_content BYTEA,  -- ⚠️ 0.76 MB por registro
    created_at TIMESTAMP
);

-- Tamaño de DB después de 1 año:
-- 1,250 PDFs × 0.76 MB = ~950 MB en tabla
-- + Índices ~100 MB
-- + Overhead ~200 MB
-- = ~1.25 GB solo para PDFs
```

**PostgreSQL no es eficiente para BLOBs grandes**

---

### **Opción 3: Object Storage (S3/Wasabi/MinIO)** 🌟 MEJOR A LARGO PLAZO

#### ✅ Pros
- **Escalabilidad infinita**: Sin límites de espacio
- **Durabilidad**: 99.999999999% (11 noves)
- **Redundancia**: Múltiples copias automáticas
- **CDN**: Acceso rápido global
- **Versionado**: Automático (opcional)
- **Backup**: Automático y distribuido
- **Costos bajos**: ~$0.01/GB/mes (Wasabi)
- **Multi-servidor**: Acceso desde cualquier lugar

#### ❌ Contras
- **Latencia**: ~100-300ms vs local
- **Costo mensual**: ~$10-50/año para 10 años
- **Dependencia externa**: Requiere internet
- **Configuración**: Más setup inicial
- **Vendor lock-in**: Depender de proveedor

#### 🏗️ Arquitectura
```
┌─────────────────────────────────────────┐
│         FastAPI Backend                 │
│  ┌───────────────────────────────────┐  │
│  │  Downloader Service               │  │
│  │  ├─ Descarga PDF                  │  │
│  │  └─ Sube a S3/Wasabi              │  │
│  └───────────────────────────────────┘  │
│              ↓                          │
│  ┌───────────────────────────────────┐  │
│  │  Object Storage (S3/Wasabi)       │  │
│  │  └─ boletines/2025/08/...         │  │
│  └───────────────────────────────────┘  │
│              ↓                          │
│  ┌───────────────────────────────────┐  │
│  │  PostgreSQL                       │  │
│  │  └─ Metadata + S3 URL             │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

#### 💰 Costos Estimados

**AWS S3:**
- Storage: $0.023/GB/mes
- 10 años (9.3 GB): ~$26/año = **$260 total**

**Wasabi** (más barato):
- Storage: $0.0059/GB/mes (4x más barato)
- 10 años (9.3 GB): ~$6.60/año = **$66 total**

**Backblaze B2:**
- Storage: $0.005/GB/mes
- 10 años (9.3 GB): ~$5.60/año = **$56 total**

---

### **Opción 4: Híbrido (Local + Nube)** 🎯 RECOMENDADA PRODUCCIÓN

#### Estrategia
```
1. Descarga → Filesystem local (rápido)
2. Procesamiento → Lee desde local (0ms latency)
3. Backup diario → Sube a S3/Wasabi (automático)
4. Retención → Mantiene últimos 30 días localmente
5. Archivo histórico → Solo en nube (libera espacio)
```

#### ✅ Ventajas
- **Mejor de ambos mundos**: Velocidad + durabilidad
- **Costo optimizado**: Solo paga storage en nube
- **Backup automático**: Sin preocupaciones
- **Escalable**: Crece sin límites
- **Resiliente**: Múltiples copias

#### 🏗️ Arquitectura
```
┌─────────────────────────────────────────────────┐
│              FastAPI Backend                    │
│  ┌─────────────────────────────────────────┐   │
│  │  1. Descarga → /tmp/boletines/          │   │
│  │  2. Procesa → DS Lab Analysis           │   │
│  │  3. Guarda metadata → PostgreSQL        │   │
│  └─────────────────────────────────────────┘   │
│              ↓                ↓                 │
│  ┌─────────────────┐   ┌─────────────────┐    │
│  │ Local Storage   │   │  S3/Wasabi      │    │
│  │ (últimos 30d)   │   │  (histórico)    │    │
│  └─────────────────┘   └─────────────────┘    │
└─────────────────────────────────────────────────┘
```

---

## 🎯 Recomendación Final

### Para Desarrollo/MVP: **Opción 1 (Filesystem Local)** ⭐
```python
# Simple, rápido, sin costos
BOLETINES_DIR = Path("/Users/germanevangelisti/watcher-agent/boletines")
```

**Porque:**
- ✅ Ya funciona
- ✅ Costo $0
- ✅ Suficiente para 10 años
- ✅ Fácil debugging
- ✅ Desarrollo ágil

### Para Producción: **Opción 4 (Híbrido)** 🌟
```python
# Local para procesamiento, nube para backup
LOCAL_CACHE = Path("/data/boletines/cache")
S3_BUCKET = "watcher-boletines-historico"
```

**Porque:**
- ✅ Velocidad local + durabilidad nube
- ✅ Backup automático
- ✅ Escalable sin límites
- ✅ Costo ~$6/año (Wasabi)
- ✅ Multi-servidor ready

---

## 🔧 Implementación Recomendada

### Fase 1: Mejorar Filesystem Actual (1-2 días)

```python
# backend/app/core/config.py
from pathlib import Path

class Settings:
    # Estructura organizada
    BOLETINES_BASE_DIR = Path("/data/boletines")
    BOLETINES_CACHE_DIR = BOLETINES_BASE_DIR / "cache"
    BOLETINES_ARCHIVE_DIR = BOLETINES_BASE_DIR / "archive"
    
    # Retención
    CACHE_RETENTION_DAYS = 30
    
    # Backup
    BACKUP_ENABLED = True
    BACKUP_DIR = Path("/backup/boletines")
```

```python
# backend/app/services/storage_service.py
from pathlib import Path
from datetime import datetime

class FileSystemStorage:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
    
    def save_boletin(self, filename: str, content: bytes) -> Path:
        """Guarda boletín con estructura año/mes"""
        # Parse fecha del filename: YYYYMMDD_N_Secc.pdf
        date_str = filename[:8]  # YYYYMMDD
        year = date_str[:4]
        month = date_str[4:6]
        
        # Crear estructura
        dir_path = self.base_dir / year / month
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo
        file_path = dir_path / filename
        file_path.write_bytes(content)
        
        return file_path
    
    def get_boletin(self, filename: str) -> bytes:
        """Obtiene boletín desde filesystem"""
        date_str = filename[:8]
        year = date_str[:4]
        month = date_str[4:6]
        
        file_path = self.base_dir / year / month / filename
        return file_path.read_bytes()
    
    def exists(self, filename: str) -> bool:
        """Verifica si existe el boletín"""
        date_str = filename[:8]
        year = date_str[:4]
        month = date_str[4:6]
        
        file_path = self.base_dir / year / month / filename
        return file_path.exists()
```

### Fase 2: Agregar Backup Automático (2-3 días)

```python
# backend/app/services/backup_service.py
import shutil
from pathlib import Path
from datetime import datetime, timedelta

class BackupService:
    def __init__(self, source_dir: Path, backup_dir: Path):
        self.source_dir = source_dir
        self.backup_dir = backup_dir
    
    def backup_daily(self):
        """Backup diario incremental"""
        today = datetime.now().strftime("%Y%m%d")
        backup_path = self.backup_dir / today
        
        # Backup incremental con rsync
        shutil.copytree(
            self.source_dir,
            backup_path,
            dirs_exist_ok=True
        )
        
        # Limpiar backups antiguos (mantener 30 días)
        self.cleanup_old_backups(days=30)
    
    def cleanup_old_backups(self, days: int = 30):
        """Elimina backups más antiguos que X días"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for backup_dir in self.backup_dir.iterdir():
            try:
                backup_date = datetime.strptime(backup_dir.name, "%Y%m%d")
                if backup_date < cutoff_date:
                    shutil.rmtree(backup_dir)
            except ValueError:
                continue

# Cron job diario (crontab)
# 0 2 * * * /usr/bin/python /path/to/run_backup.py
```

### Fase 3: Migrar a Híbrido S3 (3-5 días)

```python
# backend/app/services/s3_storage_service.py
import boto3
from pathlib import Path
from datetime import datetime

class S3Storage:
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self.s3_client = boto3.client('s3', region_name=region)
        self.bucket_name = bucket_name
    
    def upload_boletin(self, filename: str, file_path: Path):
        """Sube boletín a S3"""
        # Parse fecha
        date_str = filename[:8]
        year = date_str[:4]
        month = date_str[4:6]
        
        # Key en S3: boletines/2025/08/20250801_1_Secc.pdf
        s3_key = f"boletines/{year}/{month}/{filename}"
        
        # Upload
        self.s3_client.upload_file(
            str(file_path),
            self.bucket_name,
            s3_key,
            ExtraArgs={
                'ContentType': 'application/pdf',
                'StorageClass': 'STANDARD_IA'  # Infrequent Access (más barato)
            }
        )
        
        return f"s3://{self.bucket_name}/{s3_key}"
    
    def download_boletin(self, filename: str, dest_path: Path):
        """Descarga boletín desde S3"""
        date_str = filename[:8]
        year = date_str[:4]
        month = date_str[4:6]
        
        s3_key = f"boletines/{year}/{month}/{filename}"
        
        self.s3_client.download_file(
            self.bucket_name,
            s3_key,
            str(dest_path)
        )
    
    def get_presigned_url(self, filename: str, expiration: int = 3600):
        """Genera URL temporal para acceso directo"""
        date_str = filename[:8]
        year = date_str[:4]
        month = date_str[4:6]
        
        s3_key = f"boletines/{year}/{month}/{filename}"
        
        return self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': s3_key},
            ExpiresIn=expiration
        )

# Uso combinado
class HybridStorage:
    def __init__(self, local_storage: FileSystemStorage, s3_storage: S3Storage):
        self.local = local_storage
        self.s3 = s3_storage
    
    async def save_boletin(self, filename: str, content: bytes):
        """Guarda en local y hace backup en S3"""
        # 1. Guardar localmente
        local_path = self.local.save_boletin(filename, content)
        
        # 2. Subir a S3 en background
        s3_url = await self.s3.upload_boletin(filename, local_path)
        
        # 3. Actualizar DB con ambas ubicaciones
        await db.update_boletin(
            filename=filename,
            local_path=str(local_path),
            s3_url=s3_url
        )
        
        return local_path
    
    async def get_boletin(self, filename: str) -> bytes:
        """Obtiene boletín (primero intenta local, luego S3)"""
        # Intenta local primero
        if self.local.exists(filename):
            return self.local.get_boletin(filename)
        
        # Si no está local, descarga desde S3
        temp_path = Path(f"/tmp/{filename}")
        await self.s3.download_boletin(filename, temp_path)
        content = temp_path.read_bytes()
        
        # Opcionalmente guardar en cache local
        self.local.save_boletin(filename, content)
        
        return content
```

---

## 📋 Plan de Migración

### Cronograma Sugerido

| Fase | Duración | Prioridad | Costo |
|------|----------|-----------|-------|
| **1. Organizar filesystem** | 1-2 días | 🔴 Alta | $0 |
| **2. Backup automático** | 2-3 días | 🟡 Media | $0 |
| **3. Migrar a híbrido S3** | 3-5 días | 🟢 Baja | $6/año |

### Paso a Paso

#### Semana 1: Filesystem Mejorado
```bash
# 1. Crear estructura
mkdir -p /data/boletines/{2025,2026}/{01..12}

# 2. Mover archivos existentes
python scripts/migrate_filesystem.py

# 3. Actualizar referencias en DB
python scripts/update_db_paths.py

# 4. Probar sistema
pytest tests/test_storage.py
```

#### Semana 2: Backup
```bash
# 1. Setup backup dir
mkdir -p /backup/boletines

# 2. Configurar cron
crontab -e
# Agregar: 0 2 * * * /usr/bin/python /app/run_backup.py

# 3. Primer backup manual
python scripts/manual_backup.py

# 4. Verificar
ls -lh /backup/boletines/
```

#### Mes 2: S3 (Opcional)
```bash
# 1. Crear bucket en Wasabi
wasabi mb s3://watcher-boletines

# 2. Configurar credenciales
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."

# 3. Migrar archivos existentes
python scripts/migrate_to_s3.py

# 4. Activar modo híbrido
# En config.py: USE_S3_BACKUP = True
```

---

## 💰 Análisis de Costos

### Opción 1: Filesystem Local
- **Setup**: $0
- **Mensual**: $0
- **10 años**: $0
- **Riesgo**: Pérdida de datos si falla disco

### Opción 4: Híbrido (Local + Wasabi)
- **Setup**: $0
- **Mensual**: $0.55 (9.3 GB × $0.0059/GB)
- **10 años**: $66
- **Riesgo**: Prácticamente nulo (99.999999999% durabilidad)

**ROI**: $66 para 10 años de tranquilidad es excelente inversión

---

## ✅ Conclusión

### Para TU caso (Watcher):

1. **HOY (Desarrollo)**: 
   - ✅ Mantén filesystem local
   - ✅ Organiza por año/mes
   - ✅ Agrega backup simple

2. **PRODUCCIÓN (6 meses)**:
   - 🌟 Migra a híbrido (local + Wasabi)
   - 🌟 ~$0.55/mes = café mensual
   - 🌟 Durabilidad empresarial

3. **NO HAGAS**:
   - ❌ No guardes PDFs en PostgreSQL
   - ❌ No uses S3 premium (usa Wasabi)
   - ❌ No sobre-ingenierices para MVP

---

## 🚀 Próximo Paso Inmediato

```bash
# Reorganiza filesystem AHORA (15 minutos)
cd /Users/germanevangelisti/watcher-agent
python scripts/reorganize_boletines.py
```

¿Quieres que te genere el script de reorganización y migración? 🔧

