# 🔧 DS Lab - Troubleshooting Guide

## Error: `table red_flags has no column named result_id`

### Síntoma
```
sqlite3.OperationalError: table red_flags has no column named result_id
```

### Causa
Las tablas de la base de datos fueron creadas con una versión antigua del esquema que no incluía todas las columnas necesarias.

### Solución

#### 1. Hacer Backup de la Base de Datos Actual
```bash
cd watcher-monolith/backend
cp sqlite.db sqlite.db.backup_$(date +%Y%m%d_%H%M%S)
```

#### 2. Eliminar Base de Datos Antigua
```bash
rm sqlite.db
```

#### 3. Recrear Tablas con Esquema Correcto
```bash
python scripts/create_dslab_tables.py
```

Output esperado:
```
🚀 Creando tablas del DS Lab...
✅ Tablas creadas exitosamente:
   • boletin_documents
   • analysis_configs
   • analysis_executions
   • analysis_results
   • red_flags
   • analysis_comparisons
```

#### 4. Registrar Documentos Existentes
```bash
python scripts/register_existing_boletines.py
```

Esto escaneará el directorio `/boletines` y registrará todos los PDFs encontrados.

#### 5. Crear Configuración Inicial
```bash
python scripts/create_initial_config.py
```

#### 6. Verificar Esquema
```bash
sqlite3 sqlite.db "PRAGMA table_info(red_flags);"
```

Debe mostrar la columna `result_id`:
```
0|id|INTEGER|1||1
1|result_id|INTEGER|0||0
2|document_id|INTEGER|1||0
...
```

---

## Error: Frontend no carga - Missing Package

### Síntoma
```
Failed to resolve import "@mantine/notifications" from ...
```

### Solución
```bash
cd watcher-monolith/frontend
npm install @mantine/notifications@7.17.8
```

Asegúrate de agregar el provider en `App.tsx`:
```tsx
import { Notifications } from '@mantine/notifications';
import '@mantine/notifications/styles.css';

function App() {
  return (
    <MantineProvider>
      <Notifications />
      {/* ... resto del app */}
    </MantineProvider>
  );
}
```

---

## Error: Backend no responde

### Síntoma
```
Connection refused - localhost:8001
```

### Verificar Estado
```bash
ps aux | grep uvicorn
```

### Iniciar Backend
```bash
cd watcher-monolith/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

---

## Error: Análisis se queda "stuck"

### Verificar Progreso
```bash
curl http://localhost:8001/api/v1/dslab/analysis/executions/{ID}/progress | python -m json.tool
```

### Ver Logs del Backend
Revisa la terminal donde está corriendo uvicorn para ver errores detallados.

### Cancelar Análisis
```bash
curl -X POST http://localhost:8001/api/v1/dslab/analysis/executions/{ID}/cancel
```

---

## Error: Muchos documentos fallan durante análisis

### Verificar Integridad de PDFs
```bash
# Ver un documento específico que falló
cd boletines/2025/01
pdfinfo 20250102_1_Secc.pdf
```

### Revisar Logs de Error
Los errores de procesamiento se guardan en `analysis_executions.error_message`.

```bash
curl http://localhost:8001/api/v1/dslab/analysis/executions/{ID} | python -m json.tool | grep error_message
```

### Ajustar Timeouts
Edita `app/services/dslab_analyzer.py` si necesitas ajustar timeouts para PDFs grandes.

---

## Limpiar Todo y Empezar de Cero

Si tienes problemas persistentes:

```bash
# 1. Backup completo
cd watcher-monolith/backend
cp sqlite.db sqlite.db.full_backup_$(date +%Y%m%d_%H%M%S)

# 2. Eliminar DB
rm sqlite.db

# 3. Recrear todo
python scripts/create_dslab_tables.py
python scripts/register_existing_boletines.py
python scripts/create_initial_config.py

# 4. Verificar
sqlite3 sqlite.db "SELECT COUNT(*) FROM boletin_documents;"
sqlite3 sqlite.db "SELECT * FROM analysis_configs;"
```

---

## Verificación Rápida del Sistema

```bash
#!/bin/bash
echo "🔍 Verificando sistema DS Lab..."

# Backend
echo -n "Backend (8001): "
curl -s http://localhost:8001/api/v1/dslab/configs > /dev/null && echo "✅" || echo "❌"

# Frontend
echo -n "Frontend (3001): "
curl -s http://localhost:3001 > /dev/null && echo "✅" || echo "❌"

# Base de datos
echo -n "Documentos registrados: "
cd watcher-monolith/backend
sqlite3 sqlite.db "SELECT COUNT(*) FROM boletin_documents;"

echo -n "Configuraciones: "
sqlite3 sqlite.db "SELECT COUNT(*) FROM analysis_configs;"

echo -n "Ejecuciones: "
sqlite3 sqlite.db "SELECT COUNT(*) FROM analysis_executions;"
```

---

## Problemas Comunes y Soluciones Rápidas

### "Config no encontrada"
```bash
python scripts/create_initial_config.py
```

### "No hay documentos para analizar"
```bash
python scripts/register_existing_boletines.py
```

### "Session rollback error"
Indica un error anterior en la transacción. Reinicia el backend:
```bash
# Ctrl+C en la terminal del backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### "UI no muestra progreso"
1. Verifica que el backend esté corriendo
2. Abre DevTools (F12) → Network tab
3. Verifica que las llamadas a `/progress` devuelvan 200 OK

---

## Contacto y Reportar Bugs

Si encuentras un error que no está listado aquí:

1. Guarda los logs del backend
2. Anota los pasos para reproducir
3. Captura el error completo (con traceback)
4. Verifica la versión de los paquetes:
   ```bash
   cd watcher-monolith/backend
   pip list | grep -E "(fastapi|sqlalchemy|pdfplumber)"
   
   cd ../frontend
   npm list | grep -E "(mantine|react)"
   ```

---

**Última actualización**: 2025-11-17  
**Versión del sistema**: 1.0.0

