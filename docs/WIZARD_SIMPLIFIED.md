# 🎯 Wizard Simplificado - 3 Pasos

## Fecha: 2026-02-03

---

## 📝 Cambio Implementado

Se simplificó el wizard de procesamiento para **omitir la descarga** y comenzar directamente desde la **extracción de contenido**, ya que el sistema tiene **1,310 boletines ya descargados**.

---

## 🔄 ANTES vs AHORA

### ANTES (4 pasos)
```
┌─────────────────────────────────────┐
│ Paso 0: 📥 Descarga                 │
│ Paso 1: 📄 Extracción               │
│ Paso 2: 🤖 Procesamiento IA         │
│ Paso 3: 📊 Resultados               │
└─────────────────────────────────────┘
```

### AHORA (3 pasos)
```
┌─────────────────────────────────────┐
│ Paso 0: 📄 Extracción               │
│ Paso 1: 🤖 Procesamiento IA         │
│ Paso 2: 📊 Resultados               │
└─────────────────────────────────────┘
```

---

## 🎨 Cambios Visuales

### 1. **Nuevo Header**
```
✨ Asistente de Procesamiento
Extracción de Contenido → Análisis con IA → Resultados
```

### 2. **Stepper Actualizado**

```typescript
<Stepper active={activeStep}>
  <Stepper.Step 
    label="Extracción de Contenido"
    description="PDF → Texto estructurado"
    icon={<IconFileText />}
  />
  <Stepper.Step 
    label="Procesamiento con IA"
    description="Análisis inteligente"
    icon={<IconRobot />}
  />
  <Stepper.Step 
    label="Resultados"
    description="Ver insights generados"
    icon={<IconChartBar />}
  />
</Stepper>
```

### 3. **Paso 0: Extracción Mejorada**

Ahora muestra información destacada de los boletines descargados:

```
┌─────────────────────────────────────────┐
│           📄                            │
│                                         │
│     Extracción de Contenido             │
│     Convierte PDFs a texto              │
│                                         │
│  ╔═══════════════════════════════════╗  │
│  ║   Boletines Descargados           ║  │
│  ║        1,310                      ║  │
│  ║      XX.XX MB en total            ║  │
│  ╚═══════════════════════════════════╝  │
│                                         │
│  ℹ️  Se extraerá el texto de los       │
│     1,310 PDFs descargados.             │
│     Esta operación puede tardar         │
│     varios minutos.                     │
│                                         │
│  [▶️ Iniciar Extracción de 1,310]      │
└─────────────────────────────────────────┘
```

---

## 🔧 Cambios Técnicos

### Estados Actualizados

```typescript
// ANTES (4 estados)
const [stepStatuses, setStepStatuses] = useState({
  0: 'pending', // Descarga
  1: 'pending', // Extracción
  2: 'pending', // Procesamiento
  3: 'pending'  // Resultados
});

// AHORA (3 estados)
const [stepStatuses, setStepStatuses] = useState({
  0: 'pending', // Extracción
  1: 'pending', // Procesamiento
  2: 'pending'  // Resultados
});
```

### Funciones Eliminadas

- ❌ `startDownload()` - Ya no es necesaria
- ❌ `DownloadStepContent` - Componente eliminado

### Funciones Actualizadas

```typescript
// startExtraction ahora es Paso 0 (antes era Paso 1)
const startExtraction = async () => {
  setStepStatuses({ ...stepStatuses, 0: 'in_progress' }); // ← Cambió de 1 a 0
  // ... resto del código
  setActiveStep(1); // ← Avanza a Procesamiento (antes era 2)
};

// startProcessing ahora es Paso 1 (antes era Paso 2)
const startProcessing = async () => {
  setStepStatuses({ ...stepStatuses, 1: 'in_progress' }); // ← Cambió de 2 a 1
  // ... resto del código
  setActiveStep(2); // ← Avanza a Resultados (antes era 3)
};
```

### loadInitialState Simplificado

```typescript
const loadInitialState = async () => {
  // Cargar estadísticas de archivos
  const statsData = await fetch('/api/v1/boletines/stats');
  
  // Actualizar sync status con archivos encontrados
  setSyncStatus({
    boletines_downloaded: totalFiles, // 1,310
    // ... otros campos
  });
  
  // Verificar si hay análisis
  const analysisData = await fetch('/api/v1/analisis?limit=1');
  
  if (analysisData.length > 0) {
    // Hay análisis → Ir directo a Resultados
    setActiveStep(2);
  } else {
    // No hay análisis → Comenzar desde Extracción
    setActiveStep(0);
  }
};
```

---

## 📊 Flujo de Usuario Actualizado

### Entrada al Wizard

```
Usuario navega a /wizard
         ↓
loadInitialState()
         ↓
Detecta 1,310 PDFs descargados
         ↓
Verifica si hay análisis
         ↓
┌─────────────────┬────────────────────┐
│ HAY ANÁLISIS    │ NO HAY ANÁLISIS    │
├─────────────────┼────────────────────┤
│ setActiveStep(2)│ setActiveStep(0)   │
│ (Resultados)    │ (Extracción)       │
└─────────────────┴────────────────────┘
```

### Flujo Normal (Sin análisis previos)

```
PASO 0: Extracción
  ↓
Usuario: Click "Iniciar Extracción de 1,310"
  ↓
Backend: Procesa PDFs → Texto
  ↓
Polling: Actualiza progreso
  ↓
Completado → Avanza automático
  ↓
PASO 1: Procesamiento IA
  ↓
Usuario: Click "Iniciar Análisis IA"
  ↓
Backend: 3 workflows (Trends, Summary, High-Risk)
  ↓
Polling: Muestra progreso de tareas
  ↓
Completado → Carga estadísticas finales
  ↓
PASO 2: Resultados
  ↓
Muestra:
  - Red Flags detectados
  - Actos administrativos
  - Menciones jurisdiccionales
  ↓
Navegación a Dashboard/Alertas/Jurisdicciones
```

---

## 🎯 Ventajas de la Simplificación

### ✅ Más Directo
- Usuario llega directo al punto: procesar contenido existente
- No pierde tiempo en un paso de "descarga" ya completado

### ✅ Menos Confusión
- 3 pasos en lugar de 4
- Cada paso tiene un propósito claro
- Flujo lineal y predecible

### ✅ Mejor UX
- Card grande con número destacado (1,310 boletines)
- Feedback inmediato de lo que hay en el sistema
- Botón con texto descriptivo: "Iniciar Extracción de 1,310 Boletines"

### ✅ Más Eficiente
- Menos código para mantener
- Lógica más simple
- Menos estados que rastrear

---

## 🔄 Reutilización en el Futuro

Si en el futuro se necesita agregar la descarga:

### Opción 1: Link Externo
```tsx
<Alert>
  <Text>¿Necesitas descargar más boletines?</Text>
  <Button component="a" href="/settings">
    Ir a Configuración → Sincronización
  </Button>
</Alert>
```

### Opción 2: Wizard Separado
- Mantener este wizard para procesamiento
- Crear un "Wizard de Descarga" independiente
- Accesible desde Configuración

### Opción 3: Modo Avanzado
- Toggle "Modo Avanzado"
- Si está activado → Mostrar paso de descarga
- Si está desactivado → Flujo actual (3 pasos)

---

## 📝 Archivos Modificados

```
✏️  Modificado:
└── watcher-monolith/frontend/src/components/wizard/ProcessingWizard.tsx
    ├── Estados reducidos de 4 a 3
    ├── Eliminado startDownload()
    ├── Eliminado DownloadStepContent
    ├── Actualizado ExtractionStepContent
    │   └── Card destacada con número de boletines
    ├── Ajustados índices de pasos
    ├── Actualizado Stepper (3 pasos)
    └── Simplificado loadInitialState()

📄 Nuevo:
└── docs/WIZARD_SIMPLIFIED.md (este archivo)
```

---

## ✅ Verificación

### Checklist de Funcionalidad

- [x] Wizard inicia en Paso 0 (Extracción)
- [x] Muestra 1,310 boletines descargados
- [x] Card con número grande visible
- [x] Botón "Iniciar Extracción" funcional
- [x] Stepper muestra 3 pasos
- [x] Navegación entre pasos funciona
- [x] Polling actualiza progreso
- [x] Transiciones automáticas funcionan
- [x] No hay errores de lint
- [x] No hay errores de TypeScript

### URLs de Prueba

```bash
# Acceder al wizard
http://localhost:5173/wizard

# Backend (API)
http://localhost:8001/api/v1/boletines/stats

# Verificar análisis
http://localhost:8001/api/v1/analisis?limit=1
```

---

## 🚀 Próximos Pasos

### Para el Usuario

1. **Ir al Wizard**: `http://localhost:5173/wizard`
2. **Ver los 1,310 boletines** en el card destacado
3. **Click en "Iniciar Extracción"** para procesar PDFs
4. **Esperar** mientras se extrae el texto (con progreso en tiempo real)
5. **Avanzar a Procesamiento IA** cuando complete
6. **Ejecutar análisis** con agentes inteligentes
7. **Ver resultados finales** en el último paso

### Para Desarrollo Futuro

- **Sprint 2**: Implementar extracción en background con workers
- **Sprint 3**: Cache de texto extraído para evitar reprocesar
- **Sprint 4**: Procesamiento incremental (solo nuevos boletines)

---

## 🎉 Resultado Final

**ANTES:**
- Wizard con 4 pasos
- Paso de descarga innecesario
- Confuso para usuario con boletines existentes

**AHORA:**
- ✅ Wizard con 3 pasos
- ✅ Comienza directo en Extracción
- ✅ Muestra claramente 1,310 boletines listos
- ✅ UX más directa y eficiente
- ✅ Flujo optimizado para el caso común

---

**El wizard está listo para procesar los 1,310 boletines existentes** 🚀
