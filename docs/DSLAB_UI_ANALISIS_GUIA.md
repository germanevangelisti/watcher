# 🎨 UI de Análisis DS Lab - Guía de Uso

## 📍 Acceso

La nueva interfaz de análisis está disponible en:
```
http://localhost:3001/dslab/analysis
```

También puedes acceder desde el menú lateral: **"Ejecutar Análisis"**

---

## 🎯 Características Principales

### 1. **Configurar Análisis** 📝
Pestaña inicial donde configuras los parámetros del análisis:

#### Opciones Disponibles:
- **Configuración de Modelo**: Selecciona la versión del modelo a usar
  - Por defecto usa la configuración activa
  - Puedes ver todas las versiones disponibles

- **Rango de Fechas**: Define el período a analizar
  - Fecha de inicio
  - Fecha de fin
  - Usa los selectores de calendario para mayor facilidad

- **Secciones del Boletín**: Elige qué secciones procesar
  - 1ª Sección - Designaciones y Decretos
  - 2ª Sección - Compras y Contrataciones
  - 3ª Sección - Subsidios y Transferencias
  - 4ª Sección - Obras Públicas
  - 5ª Sección - Notificaciones Judiciales
  - Por defecto todas están seleccionadas

#### Iniciar Análisis:
1. Completa todos los campos requeridos
2. Haz clic en **"Iniciar Análisis"**
3. Automáticamente cambiará a la pestaña de progreso

---

### 2. **Monitorear Progreso** 📊
Vista en tiempo real del análisis en ejecución:

#### Visualizaciones:

**Barra de Progreso Animada**
- Muestra el porcentaje completado
- Color azul mientras procesa
- Verde al completar exitosamente
- Rojo si falla

**Métricas en Tiempo Real**
- **Procesados**: Documentos analizados / Total
- **Progreso**: Porcentaje completado
- **Fallidos**: Documentos con errores

**Documento Actual**
- Muestra el archivo que se está procesando ahora
- Actualización cada 2 segundos

**Tiempo Estimado**
- Calcula el tiempo restante basado en la velocidad actual
- Se actualiza dinámicamente

**Progreso Circular (RingProgress)**
- Visualización gráfica del progreso total
- Azul: Documentos procesados exitosamente
- Rojo: Documentos fallidos

#### Acciones Disponibles:
- **Cancelar**: Detener el análisis en cualquier momento
- El progreso se guarda y puedes verlo después

---

### 3. **Panel de Logs** 📝
Ubicado en el lado derecho durante el análisis:

#### Tipos de Logs:
- 🔵 **INFO**: Información general
  - "Iniciando análisis..."
  - "Total de documentos: 108"

- ✅ **SUCCESS**: Operaciones exitosas
  - "Análisis iniciado con ID: 3"
  - "Análisis completado"

- ⚠️ **WARNING**: Advertencias
  - "Análisis cancelado por el usuario"

- ❌ **ERROR**: Errores
  - "Error iniciando análisis"

#### Características:
- Muestra timestamp de cada evento
- Auto-scroll a los logs más recientes
- Botón para limpiar logs
- Persistente durante toda la sesión

---

### 4. **Ver Resultados** 📈
Pestaña que se activa automáticamente al completar el análisis:

#### Cards de Resumen:
1. **Documentos Procesados**: X/Y documentos
2. **Score Promedio**: Transparency score promedio (0-100)
3. **Red Flags**: Total de problemas detectados
4. **Duración**: Tiempo total del análisis

#### Distribución de Riesgo:
Tabla con breakdown completo:
- **HIGH** (Alto): Documentos de alto riesgo 🔴
- **MEDIUM** (Medio): Riesgo moderado 🟡
- **LOW** (Bajo): Bajo riesgo 🟢

Incluye:
- Cantidad de documentos por nivel
- Porcentaje del total

#### Red Flags por Severidad:
Tabla detallada de problemas encontrados:
- **CRITICAL**: Críticos
- **HIGH**: Alto
- **MEDIUM**: Medio
- **LOW**: Bajo

#### Acciones Post-Análisis:
- **Ver Resultados Detallados**: Abre API con JSON completo
- **Exportar Reporte**: Descarga resultados (próximamente)

---

## 🎬 Flujo de Trabajo Típico

### Análisis Rápido de un Mes
```
1. Ir a "Ejecutar Análisis"
2. Seleccionar:
   - Config: watcher_baseline v1.0.0
   - Inicio: 2025-01-01
   - Fin: 2025-01-31
   - Secciones: Todas
3. Click "Iniciar Análisis"
4. Ver progreso en tiempo real
5. Cuando termine, revisar resultados
6. Identificar documentos de alto riesgo
```

### Análisis Comparativo
```
1. Ejecutar análisis con config v1.0
2. Anotar el ID de ejecución
3. Modificar parámetros en configs
4. Ejecutar análisis con config v1.1 (mismas fechas)
5. Usar endpoint de comparaciones para ver diferencias
```

---

## 💡 Tips y Mejores Prácticas

### Optimización de Rendimiento
- **Análisis pequeños primero**: Prueba con 1 mes antes de todo el año
- **Secciones específicas**: Si solo te interesan compras, analiza solo sección 2
- **Horarios**: Ejecuta análisis largos en horarios de menor uso

### Interpretación de Resultados
- **Score < 30**: Revisar manualmente, probable problema
- **Score 30-50**: Monitorear, posible área de mejora
- **Score > 70**: Documento transparente, bajo riesgo

### Red Flags
- **Critical/High**: Requieren acción inmediata
- **Medium**: Revisar cuando sea posible
- **Low**: Informativo, no urgente

### Logs
- Guarda los logs si encuentras errores
- Útiles para debug si algo falla
- Limpiar logs entre ejecuciones para mayor claridad

---

## 🔄 Actualización en Tiempo Real

### Polling Automático
La UI se actualiza cada **2 segundos** mientras el análisis corre:
- Progreso actualizado
- Documento actual
- Tiempo estimado
- Logs nuevos

### Notificaciones
Recibirás notificaciones al:
- ✅ Iniciar análisis exitosamente
- ✅ Completar análisis
- ⚠️ Cancelar análisis
- ❌ Fallar análisis

---

## 🎨 Estados Visuales

### Colores de Status:
- **Azul**: En progreso (running)
- **Verde**: Completado exitosamente (completed)
- **Rojo**: Falló (failed)
- **Amarillo**: Cancelado (cancelled)

### Badges:
- 🔴 **HIGH**: Riesgo alto
- 🟡 **MEDIUM**: Riesgo medio
- 🟢 **LOW**: Riesgo bajo

---

## 📊 Ejemplo de Análisis Completo

### Configuración:
```
Config: watcher_baseline v1.0.0
Fecha inicio: 2025-01-01
Fecha fin: 2025-01-31
Secciones: Todas (1-5)
```

### Durante el Análisis:
```
Progreso: 45/108 (41.7%)
Estado: running
Procesando: 20250115_3_Secc.pdf
Tiempo restante: 2m 30s
Fallidos: 2
```

### Resultados Finales:
```
✅ Documentos Procesados: 106/108
📊 Score Promedio: 52.3/100
🚨 Red Flags: 87
⏱️ Duración: 4m 5s

Distribución de Riesgo:
- HIGH: 15 documentos (14.2%)
- MEDIUM: 45 documentos (42.5%)
- LOW: 46 documentos (43.3%)

Red Flags por Severidad:
- CRITICAL: 5
- HIGH: 20
- MEDIUM: 42
- LOW: 20
```

---

## 🔧 Troubleshooting

### El análisis no inicia
- ✅ Verifica que el backend esté corriendo (puerto 8001)
- ✅ Completa todos los campos requeridos
- ✅ Verifica que haya documentos en el rango seleccionado

### Progreso se congela
- Refrescar la página (el análisis sigue corriendo en el backend)
- Verificar logs del backend
- Usar el endpoint de progreso manual: `/api/v1/dslab/analysis/executions/{id}/progress`

### Muchos documentos fallan
- Revisar logs para ver patrones
- Verificar integridad de PDFs
- Ajustar timeouts en configuración

### Score muy bajo en todos
- Normal si los documentos realmente tienen problemas
- Considera ajustar thresholds si son muchos falsos positivos
- Compara con análisis de agosto (baseline)

---

## 🚀 Próximas Funcionalidades

### En Desarrollo:
- ⏳ Exportación de reportes en PDF
- ⏳ Gráficos interactivos de tendencias
- ⏳ Filtros avanzados en resultados
- ⏳ Comparador visual de ejecuciones
- ⏳ Notificaciones por email al completar

---

## 📚 Recursos Adicionales

- **API Docs**: Ver `/docs` en el backend para referencia completa
- **Guía de Uso Completa**: `/docs/DSLAB_GUIA_USO_COMPLETA.md`
- **Sistema Implementado**: `/SISTEMA_DSLAB_COMPLETO.md`

---

**Versión de la UI**: 1.0.0  
**Última actualización**: 2025-11-17  
**Compatibilidad**: Backend API v1

