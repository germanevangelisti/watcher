# 🎨 Wizard de Procesamiento - Rediseño UI Completo

## ✨ Resumen

Se ha implementado un **Asistente de Procesamiento Wizard** completamente nuevo que transforma la experiencia del usuario al procesar boletines oficiales. El wizard guía al usuario paso a paso a través de todo el flujo de trabajo con visualizaciones claras y feedback en tiempo real.

## 🎯 Objetivo

Hacer visible y transparente cada etapa del procesamiento de boletines:
1. **📥 Descarga** → Obtener PDFs del BOE
2. **📄 Extracción** → Convertir PDF a texto
3. **🤖 Procesamiento** → Análisis con agentes IA
4. **📊 Resultados** → Ver insights generados

## 🏗️ Arquitectura

### Componentes Creados

```
watcher-monolith/frontend/src/
├── components/wizard/
│   └── ProcessingWizard.tsx      # Componente principal del wizard
├── pages/
│   └── WizardPage.tsx             # Página contenedora
└── routes/index.tsx               # Ruta /wizard agregada
```

### Integración con Backend

El wizard se conecta a **endpoints reales**:

- **Descarga**: `/api/v1/sync/start` + polling a `/api/v1/sync/status`
- **Extracción**: `/api/v1/boletines/process-batch`
- **Procesamiento**: `/api/v1/workflows` (crear + ejecutar)
- **Resultados**: `/api/v1/alertas/stats`, `/api/v1/menciones/stats`

## 🎨 Características Visuales

### 1. **Stepper Interactivo**
- **4 pasos claramente diferenciados** con íconos y colores
- **Estados visuales**: pendiente (gris), en progreso (azul), completado (verde), error (rojo)
- **Loading indicators** integrados en cada step
- **Transiciones automáticas** al completar cada etapa

### 2. **Cards de Progreso en Tiempo Real**

#### Descarga
```tsx
- Barra de progreso animada
- Estadísticas en vivo:
  • Boletines pendientes
  • Boletines descargados
  • Boletines fallidos
- Mensaje de operación actual
```

#### Extracción
```tsx
- Ring Progress circular
- Contador: procesados / total
- Porcentaje visual
```

#### Procesamiento IA
```tsx
- Barra de progreso por tareas
- Loader animado
- Conteo de tareas completadas
```

#### Resultados
```tsx
- 3 Cards con métricas finales:
  • Red Flags (alertas de riesgo)
  • Actos Administrativos procesados
  • Menciones Jurisdiccionales detectadas
- Botones de navegación a secciones relevantes
```

### 3. **Polling Inteligente**

El wizard usa **polling automático** para actualizar el estado en tiempo real:

```typescript
// Descarga y extracción
interval = setInterval(async () => {
  const status = await fetch('/api/v1/sync/status');
  // Actualizar UI cada 2-3 segundos
}, 2000);

// Procesamiento IA
interval = setInterval(async () => {
  const execStatus = await fetch(`/api/v1/workflows/executions/${id}`);
  // Verificar progreso de workflows
}, 3000);
```

Los intervals se **limpian automáticamente** cuando:
- La etapa se completa
- Hay un error
- El usuario resetea el wizard

### 4. **Manejo de Errores Visual**

```tsx
{status === 'error' && (
  <Alert icon={<IconX />} color="red">
    Error: {mensaje_detallado}
  </Alert>
)}
```

## 🚀 Flujo de Usuario

### Paso 0: Estado Inicial
```
Usuario llega al wizard
  ↓
Sistema carga sync_status actual
  ↓
Determina en qué etapa está el sistema
  ↓
Posiciona el stepper correctamente
```

### Paso 1: Descarga (Step 0)
```
Usuario: Click en "Iniciar Descarga"
  ↓
Backend: POST /api/v1/sync/start
  ↓
Frontend: Inicia polling cada 2s
  ↓
Actualiza stats en tiempo real:
  - Barra de progreso
  - Counters (pendientes/descargados/fallidos)
  - Mensaje de operación
  ↓
Al completar: Avanza automáticamente al Step 1
```

### Paso 2: Extracción (Step 1)
```
Usuario: Click en "Iniciar Extracción"
  ↓
Backend: POST /api/v1/boletines/process-batch
  ↓
Frontend: Polling del sync_status
  ↓
Ring Progress circular muestra:
  - % completado
  - N procesados / N total
  ↓
Al completar: Avanza al Step 2
```

### Paso 3: Procesamiento IA (Step 2)
```
Usuario: Click en "Iniciar Análisis IA"
  ↓
Backend: 
  1. Crear workflow con 3 tareas:
     - Trend Analysis
     - Monthly Summary
     - High-Risk Detection
  2. Ejecutar workflow
  ↓
Frontend: Polling de execution status
  ↓
Muestra progreso:
  - Barra de progreso
  - Tareas completadas / total
  - Loader animado
  ↓
Al completar: Carga estadísticas finales
  ↓
Avanza al Step 3
```

### Paso 4: Resultados (Step 3)
```
Sistema: Carga stats finales en paralelo
  - Alertas (red flags)
  - Actos administrativos
  - Menciones jurisdiccionales
  ↓
Muestra cards con números
  ↓
Ofrece navegación a:
  - Dashboard principal
  - Página de alertas
  - Página de jurisdicciones
```

## 🎯 Accesibilidad

### Navegación
- **Navbar**: Nuevo enlace "Asistente" con ícono de varita mágica (`IconWand`)
- **URL directa**: `/wizard`
- **Destacado visualmente** en el menú principal

### Botones de Acción
- **Tamaño grande** (`size="lg"`) para fácil interacción
- **Íconos descriptivos** en cada botón
- **Estados disabled** durante operaciones
- **Loading states** integrados

### Feedback Visual
- **Colores semánticos**:
  - Azul → En progreso
  - Verde → Completado
  - Rojo → Error
  - Gris → Pendiente
- **Animaciones suaves** (fade in/out)
- **Progress indicators** con valores numéricos

## 🔧 Configuración

### Requisitos Previos
- Backend corriendo en `http://localhost:8001`
- Frontend corriendo en `http://localhost:5173`
- Base de datos con tablas de `sync_state`, `boletines`, `workflows`

### Endpoints Requeridos

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/api/v1/sync/status` | GET | Estado actual de sincronización |
| `/api/v1/sync/start` | POST | Iniciar descarga |
| `/api/v1/boletines/process-batch` | POST | Procesar PDFs a texto |
| `/api/v1/workflows` | POST | Crear workflow |
| `/api/v1/workflows/{id}/execute` | POST | Ejecutar workflow |
| `/api/v1/workflows/executions/{id}` | GET | Estado de ejecución |
| `/api/v1/alertas/stats` | GET | Estadísticas de alertas |
| `/api/v1/menciones/stats` | GET | Estadísticas de menciones |

## 📊 Métricas y Datos

### Sync Status (Backend)
```typescript
interface SyncStatus {
  status: 'idle' | 'syncing' | 'processing' | 'completed' | 'error';
  boletines_pending: number;
  boletines_downloaded: number;
  boletines_processed: number;
  boletines_failed: number;
  current_operation: string | null;
  error_message: string | null;
}
```

### Workflow Execution (Backend)
```typescript
interface WorkflowExecution {
  id: number;
  workflow_id: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  task_count: number;
  completed_tasks: number;
  started_at: string;
  completed_at: string | null;
}
```

### Final Stats (Agregadas)
```typescript
interface FinalStats {
  redFlags: number;      // De /api/v1/alertas/stats
  actos: number;         // De /api/v1/boletines/status
  menciones: number;     // De /api/v1/menciones/stats
}
```

## 🎬 Demo Visual

### Vista del Stepper
```
┌─────────────────────────────────────────────────────────┐
│  🪄 Asistente de Procesamiento                         │
│  Descarga → Extracción → Análisis IA → Resultados      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ●────────●────────○────────○                           │
│  ✓ Descarga  ✓ Extracción  ⏰ Análisis  Resultados     │
│  PDFs del BOE  PDF→Texto   Agentes IA  Ver insights    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Vista de Progreso (Descarga)
```
┌─────────────────────────────────────────────────────────┐
│                     📥                                  │
│                                                         │
│         Descarga de Boletines Oficiales                │
│                                                         │
│  ████████████████░░░░░░░░░░  60%                       │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │Pendientes│  │Descargados│  │Fallidos  │            │
│  │   450    │  │   270     │  │    3     │            │
│  └──────────┘  └──────────┘  └──────────┘            │
│                                                         │
│  Descargando boletines de Enero 2025...                │
└─────────────────────────────────────────────────────────┘
```

### Vista de Resultados Finales
```
┌─────────────────────────────────────────────────────────┐
│                     📊                                  │
│                                                         │
│           🎉 ¡Procesamiento Completado!                 │
│                                                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐         │
│  │RED FLAGS  │  │   ACTOS   │  │ MENCIONES │         │
│  │   1,534   │  │    856    │  │    423    │         │
│  │Alto riesgo│  │Procesados │  │Jurisdicc. │         │
│  └───────────┘  └───────────┘  └───────────┘         │
│                                                         │
│  ✨ Todos los sistemas listos                          │
│                                                         │
│  [Dashboard →]  [Ver Alertas]  [Jurisdicciones]       │
└─────────────────────────────────────────────────────────┘
```

## 🔄 Funcionalidad de Reset

El botón **"Reiniciar"** (esquina superior derecha) permite:
- Volver al Step 0
- Limpiar todos los estados
- Cancelar polling activo
- Resetear contadores

Útil para:
- Iniciar un nuevo ciclo de procesamiento
- Recuperarse de errores
- Probar el wizard desde cero

## 🎯 Mejoras Futuras (Sprint 2)

1. **Persistencia de Estado**
   - Guardar progreso del wizard en localStorage
   - Recuperar automáticamente si el usuario sale y vuelve

2. **Notificaciones Push**
   - Alertas del navegador cuando cada step completa
   - Útil si el usuario está en otra pestaña

3. **Logs Detallados**
   - Timeline expandible con cada operación
   - Ver logs en tiempo real del procesamiento

4. **Modo Avanzado**
   - Configurar parámetros de cada step
   - Seleccionar rango de fechas
   - Elegir tipos de análisis específicos

5. **Cancelación de Operaciones**
   - Botón "Detener" durante cada step
   - Rollback inteligente de cambios

6. **Estimaciones de Tiempo**
   - Calcular tiempo restante basado en velocidad
   - Mostrar ETA (Estimated Time of Arrival)

## 📝 Conclusión

El nuevo **Wizard de Procesamiento** transforma completamente la experiencia de usuario al:

✅ **Hacer visible lo invisible**: Cada etapa del procesamiento está clara  
✅ **Feedback en tiempo real**: El usuario siempre sabe qué está pasando  
✅ **Guía paso a paso**: No hay confusión sobre qué hacer next  
✅ **Métricas claras**: Estadísticas concretas de todo el procesamiento  
✅ **Integración real**: Conectado a todos los endpoints del backend  
✅ **Diseño hermoso**: UI moderna con Mantine + animaciones  

Este wizard establece un **nuevo estándar** para la interfaz de usuario de Watcher Agent, priorizando la transparencia y la experiencia del usuario.

---

**Acceso**: `http://localhost:5173/wizard`  
**Menú**: Navbar → "Asistente" (ícono de varita mágica)
