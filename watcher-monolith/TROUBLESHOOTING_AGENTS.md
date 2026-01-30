# 🔧 Troubleshooting - Sistema de Agentes

## ❌ Error: 404 en rutas de agentes

### Síntoma
```
Failed to load resource: the server responded with a status of 404 (Not Found)
/api/v1/workflows
/api/v1/agents/health
```

### Causa
El servidor backend necesita reiniciarse para cargar los nuevos endpoints de agentes.

### ✅ Solución

#### Paso 1: Detener el servidor
Si el servidor está corriendo, detenerlo con `Ctrl+C`

#### Paso 2: Verificar las rutas
```bash
cd watcher-monolith/backend
python test_api_routes.py
```

Este script mostrará:
- ✅ Rutas disponibles por categoría
- ❌ Rutas faltantes
- 🎯 Estado de rutas críticas

#### Paso 3: Reiniciar el servidor
```bash
uvicorn app.main:app --reload --port 8001
```

Deberías ver en los logs algo como:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8001
```

#### Paso 4: Verificar en el navegador
Abrir: http://localhost:8001/docs

Deberías ver secciones para:
- **agents**: Endpoints de agentes
- **workflows**: Endpoints de workflows
- **feedback**: Endpoints de feedback
- **observability**: Endpoints de observability
- **websocket**: WebSocket endpoint

---

## ❌ Error: workflows.filter is not a function

### Síntoma
```
Uncaught TypeError: workflows.filter is not a function
at AgentDashboard
```

### Causa
El frontend intentó acceder a la API antes de que el backend estuviera listo, y recibió un error en lugar de un array.

### ✅ Solución

**Ya está arreglado en el código**, pero si vuelve a ocurrir:

1. **Recargar la página** (F5) después de que el backend esté corriendo
2. **Limpiar caché** del navegador si persiste

---

## ❌ Error: OpenAI API Key no encontrada

### Síntoma
```
OpenAI API key no encontrada - chat funcionará con fallback
```

### ✅ Solución

La API key ya está configurada en `backend/app/core/agent_config.py`.

Si necesitas cambiarla:

1. **Editar agent_config.py**:
```python
openai_api_key: str = "sk-tu-nueva-key-aqui"
```

2. **O usar variable de entorno**:
```bash
# En .env
OPENAI_API_KEY=sk-tu-key-aqui
```

3. **Verificar configuración**:
```bash
cd backend
python check_config.py
```

---

## 🚀 Checklist de Inicio

Antes de usar el sistema, verificar:

```bash
# 1. Backend corriendo
curl http://localhost:8001/api/v1/agents/health

# 2. Frontend corriendo
# Abrir: http://localhost:3001

# 3. Verificar rutas disponibles
cd backend
python test_api_routes.py

# 4. Verificar configuración
python check_config.py
```

---

## 📍 Puertos Correctos

| Servicio | Puerto | URL |
|----------|--------|-----|
| Backend | 8001 | http://localhost:8001 |
| Frontend | 3001 | http://localhost:3001 |
| Frontend Dev (Vite) | 5173 | http://localhost:5173 |

**Nota**: El frontend puede estar en 3001 o 5173 dependiendo de cómo se inició.

---

## 🔄 Reinicio Limpio del Sistema

Si algo no funciona, reinicio completo:

### 1. Detener todo
```bash
# Ctrl+C en todas las terminales
```

### 2. Limpiar y reiniciar backend
```bash
cd watcher-monolith/backend

# Verificar configuración
python check_config.py

# Verificar rutas
python test_api_routes.py

# Iniciar servidor
uvicorn app.main:app --reload --port 8001
```

### 3. Reiniciar frontend
```bash
cd watcher-monolith/frontend

# Limpiar caché
rm -rf node_modules/.vite

# Iniciar
npm run dev
```

### 4. Verificar
```bash
# Backend health
curl http://localhost:8001/api/v1/agents/health

# Frontend
open http://localhost:3001/agents
```

---

## 🐛 Errores Comunes y Soluciones

### Error: "Module not found"
```bash
# Reinstalar dependencias
cd backend
pip install -r requirements.txt
```

### Error: "Port already in use"
```bash
# Encontrar proceso usando el puerto
lsof -ti:8001 | xargs kill -9

# O usar otro puerto
uvicorn app.main:app --reload --port 8002
```

### Error: "CORS policy"
Verificar que el backend tiene configurado CORS para el frontend:
```python
# En app/main.py
allow_origins=["http://localhost:5173", "http://localhost:3001"]
```

### Frontend no se conecta al backend
1. Verificar que el puerto del backend es 8001
2. Verificar que el frontend apunta a localhost:8001
3. Ver la consola del navegador para errores específicos

---

## 📊 Logs Útiles

### Ver logs del backend
```bash
# Los logs aparecen en la terminal donde corre uvicorn
# Buscar líneas como:
INFO:     127.0.0.1:54321 - "GET /api/v1/agents/health HTTP/1.1" 200 OK
```

### Ver logs del frontend
```bash
# Abrir Developer Tools (F12)
# Tab: Console
# Buscar errores en rojo
```

### Ver requests de red
```bash
# Developer Tools > Network
# Filtrar por "XHR" o "Fetch"
# Ver qué requests fallan
```

---

## ✅ Sistema Funcionando Correctamente

Deberías ver:

### En el backend (terminal):
```
INFO:     Started server process
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8001
```

### En http://localhost:8001/docs:
- Secciones para agents, workflows, feedback, observability
- Endpoints en verde (no en rojo)

### En http://localhost:3001/agents:
- Agent Status Monitor mostrando agentes activos
- Cards de agentes con estado "active"
- Sin errores en la consola del navegador

### En la consola del navegador:
```
✓ Agents API available
✓ Workflows loaded
✓ No errors
```

---

## 🆘 Soporte

Si sigues teniendo problemas:

1. **Verificar versiones**:
```bash
python --version  # Debe ser 3.9+
node --version    # Debe ser 16+
```

2. **Verificar dependencias**:
```bash
cd backend
python check_config.py
```

3. **Verificar rutas**:
```bash
cd backend
python test_api_routes.py
```

4. **Logs completos**:
```bash
# Guardar logs del backend
uvicorn app.main:app --reload --port 8001 > backend.log 2>&1
```

---

**Última actualización**: Los archivos de frontend ya están corregidos para manejar errores de API correctamente. Solo necesitas **reiniciar el backend** para que los nuevos endpoints estén disponibles.





