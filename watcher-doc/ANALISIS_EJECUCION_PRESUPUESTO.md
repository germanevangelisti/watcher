# 📊 Análisis: Próximos Pasos para Datos de Ejecución del Presupuesto

**Fecha:** Diciembre 2025  
**Estado Actual:** ✅ Presupuesto Base Cargado | ⚠️ Ejecución Parcial

---

## 🎯 Estado Actual del Sistema

### ✅ **Datos Disponibles**

#### 1. **Presupuesto Base 2025** ✅ COMPLETO
- **1,289 programas** cargados en base de datos
- **44 organismos únicos** identificados
- **375 programas únicos** consolidados
- **Montos iniciales y vigentes** por programa
- **Fuente:** Archivos Excel de presupuesto inicial

**Top 3 Organismos:**
1. Ministerio de Educación - $442,096,859,444
2. Ministerio de Salud - $211,516,827,339
3. Ministerio de Economía y Gestión Pública - $128,353,279,379

#### 2. **Ejecución Baseline Marzo 2025** ⚠️ PARCIAL
- **4 archivos Excel procesados:**
  - Gastos Administración Central - Marzo 2025 (1,049 registros)
  - Gastos EMAEE - Marzo 2025 (240 registros)
  - Recursos Administración Central - Marzo 2025
  - Recursos EMAEE - Marzo 2025
- **Datos:** Solo acumulado hasta marzo 2025
- **Limitación:** No hay datos más recientes en Excel

#### 3. **Ejecución Extraída de Boletines** ⚠️ INCOMPLETO
- **Boletines procesados:** 5 de 99 (modo test)
- **Actos extraídos:** 9 actos administrativos
- **Ejecuciones detectadas:** Limitadas
- **Vinculación:** 4 actos vinculados (44.4%)

---

## 🚨 Gaps Identificados

### 1. **Falta de Datos Actualizados de Ejecución**
- ❌ Solo se tienen datos hasta marzo 2025
- ❌ No hay archivos Excel de ejecución más recientes (abril-diciembre 2025)
- ❌ No hay sistema de actualización periódica

### 2. **Procesamiento Incompleto de Boletines**
- ❌ Solo 5 de 99 boletines procesados (5%)
- ❌ Potencial de ~180+ actos administrativos sin procesar
- ❌ Ejecuciones presupuestarias no detectadas en 94 boletines

### 3. **Vinculación Mejorable**
- ⚠️ Solo 44.4% de actos vinculados con programas
- ⚠️ Score uniforme de 0.700 (confianza media)
- ⚠️ Falta detección de partidas presupuestarias en texto

### 4. **Falta de Comparación Temporal**
- ❌ No hay comparación ejecución vs presupuesto por período
- ❌ No hay alertas de desvíos presupuestarios
- ❌ No hay análisis de tendencias

---

## 🎯 Próximos Pasos Recomendados

### **FASE 1: Obtener Datos de Ejecución Actualizados** 🔴 PRIORITARIO

#### **Opción A: Archivos Excel Oficiales (Recomendado)**
**Objetivo:** Obtener archivos Excel de ejecución presupuestaria más recientes

**Acciones:**
1. **Identificar fuente de datos:**
   - Portal de Datos Abiertos de la Provincia de Córdoba
   - Ministerio de Economía y Gestión Pública
   - Dirección de Presupuesto
   - Portal de Transparencia

2. **Buscar archivos:**
   - Ejecución presupuestaria acumulada (trimestral o mensual)
   - Formato esperado: Similar a "Gastos Administración Central - Acumulado [Período] 2025.xlsx"
   - Períodos necesarios: Abril, Mayo, Junio, Julio, Agosto, Septiembre, Octubre, Noviembre, Diciembre 2025

3. **Estructura esperada:**
   ```
   Columnas requeridas:
   - ORGANISMO / JURISDICCION
   - PROGRAMA / SUBPROGRAMA
   - PARTIDA / INCISO
   - PRESUPUESTADO / CREDITO INICIAL
   - EJECUTADO / DEVENGADO / ACUMULADO
   - DESCRIPCION / CONCEPTO
   ```

4. **Procesar archivos:**
   ```bash
   cd watcher-monolith/backend
   python scripts/parse_excel_presupuesto.py
   python scripts/populate_budget.py
   ```

**Resultado esperado:**
- Datos de ejecución actualizados hasta el período más reciente disponible
- Comparación ejecución vs presupuesto por período
- Alertas de desvíos automáticas

---

#### **Opción B: Extracción Masiva de Boletines** 🔴 ALTERNATIVA

**Objetivo:** Procesar los 99 boletines para extraer ejecuciones presupuestarias

**Acciones:**
1. **Procesar todos los boletines:**
   ```bash
   cd watcher-monolith/backend
   python scripts/process_boletines_actos.py --all
   # O usar el batch processor
   python -m app.services.batch_processor
   ```

2. **Mejorar extracción de ejecuciones:**
   - Expandir patterns de regex para montos
   - Mejorar detección de partidas presupuestarias
   - Identificar tipos de operación (gasto, transferencia, subsidio, obra)
   - Extraer beneficiarios y conceptos

3. **Vincular ejecuciones con programas:**
   - Mejorar matching semántico
   - Agregar detección de partidas en texto
   - Usar embeddings para matching más preciso

**Resultado esperado:**
- ~180+ actos administrativos extraídos
- Ejecuciones presupuestarias detectadas en todos los boletines
- Vinculación mejorada con programas

---

### **FASE 2: Sistema de Actualización Periódica** 🟡 MEDIANO PLAZO

**Objetivo:** Automatizar la obtención y procesamiento de datos de ejecución

**Acciones:**
1. **Script de descarga automática:**
   - Web scraper para portal de datos abiertos
   - Detección de nuevos archivos Excel
   - Validación de formato antes de procesar

2. **Pipeline de actualización:**
   ```python
   # watcher-monolith/backend/scripts/update_ejecucion.py
   - Descargar archivos nuevos
   - Procesar y normalizar
   - Actualizar base de datos
   - Generar alertas de cambios
   ```

3. **Scheduler:**
   - Cron job o task scheduler
   - Ejecución mensual/trimestral
   - Notificaciones de actualización

**Resultado esperado:**
- Datos siempre actualizados
- Procesamiento automático
- Alertas de cambios significativos

---

### **FASE 3: Mejora de Vinculación y Análisis** 🟢 CORTO PLAZO

**Objetivo:** Mejorar precisión de vinculación y análisis de ejecución

**Acciones:**
1. **Mejorar detección de partidas:**
   ```python
   # Patrones a agregar:
   - "Partida X.X.X"
   - "Inciso X.X"
   - "Capítulo X"
   - "Artículo X del presupuesto"
   ```

2. **Matching con embeddings:**
   - Usar modelos de embeddings para matching semántico
   - Comparar descripciones de programas vs conceptos de ejecución
   - Score de confianza más preciso

3. **Análisis de desvíos:**
   - Comparar ejecución vs presupuesto por período
   - Detectar desvíos significativos (>10%, >20%)
   - Alertas automáticas de desvíos

**Resultado esperado:**
- Tasa de vinculación >80%
- Scores de confianza más precisos
- Alertas de desvíos automáticas

---

### **FASE 4: Dashboard de Ejecución** 🟢 CORTO PLAZO

**Objetivo:** Visualizar ejecución presupuestaria en tiempo real

**Acciones:**
1. **Métricas de ejecución:**
   - Porcentaje de ejecución global
   - Ejecución por organismo
   - Ejecución por programa
   - Comparación período vs período

2. **Gráficos:**
   - Evolución temporal de ejecución
   - Comparación ejecución vs presupuesto
   - Top programas por ejecución
   - Alertas de desvíos

3. **Filtros:**
   - Por período (mes, trimestre, año)
   - Por organismo
   - Por tipo de operación
   - Por nivel de riesgo

**Resultado esperado:**
- Dashboard interactivo de ejecución
- Visualización clara de desvíos
- Alertas visibles

---

## 📋 Plan de Acción Inmediato

### **Semana 1: Obtener Datos Actualizados**
- [ ] Identificar fuente de archivos Excel de ejecución
- [ ] Descargar archivos más recientes disponibles
- [ ] Procesar y cargar en base de datos
- [ ] Validar datos cargados

### **Semana 2: Procesar Boletines Completos**
- [ ] Ejecutar procesamiento de 99 boletines
- [ ] Extraer todas las ejecuciones presupuestarias
- [ ] Vincular con programas
- [ ] Validar calidad de extracción

### **Semana 3: Mejoras de Vinculación**
- [ ] Mejorar detección de partidas
- [ ] Implementar matching con embeddings
- [ ] Aumentar tasa de vinculación a >80%
- [ ] Validar precisión

### **Semana 4: Análisis y Dashboard**
- [ ] Implementar comparación ejecución vs presupuesto
- [ ] Crear alertas de desvíos
- [ ] Mejorar dashboard con métricas de ejecución
- [ ] Documentar resultados

---

## 🔍 Fuentes de Datos Potenciales

### **1. Portal de Datos Abiertos Córdoba**
- URL: `https://datosabiertos.cba.gov.ar/`
- Buscar: "Ejecución Presupuestaria", "Presupuesto", "Gastos Públicos"
- Formato: Excel, CSV

### **2. Ministerio de Economía y Gestión Pública**
- Dirección de Presupuesto
- Informes de ejecución trimestrales/mensuales
- Contacto directo para acceso a datos

### **3. Boletines Oficiales**
- Ya disponibles: 99 boletines de agosto 2025
- Procesar todos para extraer ejecuciones
- Buscar boletines de otros meses

### **4. Portal de Transparencia**
- Informes de gestión
- Ejecución presupuestaria por organismo
- Metas y resultados

---

## 📊 Métricas de Éxito

### **Corto Plazo (1 mes)**
- ✅ Datos de ejecución actualizados hasta período más reciente
- ✅ 99 boletines procesados
- ✅ >150 actos administrativos extraídos
- ✅ Tasa de vinculación >70%

### **Mediano Plazo (3 meses)**
- ✅ Sistema de actualización automática funcionando
- ✅ Tasa de vinculación >85%
- ✅ Dashboard de ejecución operativo
- ✅ Alertas de desvíos automáticas

### **Largo Plazo (6 meses)**
- ✅ Datos históricos completos (2024-2025)
- ✅ Análisis predictivo de ejecución
- ✅ Reportes automáticos
- ✅ API pública de datos

---

## 🛠️ Scripts y Herramientas Disponibles

### **Scripts Existentes:**
1. `parse_excel_presupuesto.py` - Parsear archivos Excel
2. `populate_budget.py` - Cargar presupuesto en BD
3. `process_boletines_actos.py` - Procesar boletines
4. `vincular_actos_presupuesto.py` - Vincular actos con programas
5. `batch_processor.py` - Procesamiento masivo

### **Servicios Disponibles:**
1. `ActoAdministrativoParser` - Extraer actos de boletines
2. `SemanticMatcher` - Matching semántico
3. `BatchProcessor` - Procesamiento paralelo
4. `AlertGenerator` - Generar alertas

### **APIs Disponibles:**
1. `GET /api/v1/presupuesto/programas` - Listar programas
2. `GET /api/v1/presupuesto/programas/{id}` - Detalle con ejecución
3. `GET /api/v1/presupuesto/programas/{id}/ejecucion` - Ejecuciones
4. `GET /api/v1/metricas/generales` - Métricas generales

---

## 💡 Recomendaciones Finales

### **Prioridad 1: Obtener Datos Actualizados** 🔴
- **Acción inmediata:** Buscar y descargar archivos Excel de ejecución más recientes
- **Impacto:** Alto - Permite análisis real de ejecución vs presupuesto
- **Esfuerzo:** Bajo - Reutilizar scripts existentes

### **Prioridad 2: Procesar Boletines Completos** 🔴
- **Acción inmediata:** Ejecutar procesamiento de 99 boletines
- **Impacto:** Alto - Extrae ejecuciones no detectadas
- **Esfuerzo:** Medio - Requiere validación de resultados

### **Prioridad 3: Mejorar Vinculación** 🟡
- **Acción:** Mejorar detección de partidas y matching
- **Impacto:** Medio - Mejora calidad de análisis
- **Esfuerzo:** Medio - Requiere desarrollo

### **Prioridad 4: Automatización** 🟢
- **Acción:** Sistema de actualización periódica
- **Impacto:** Alto - Mantiene datos actualizados
- **Esfuerzo:** Alto - Requiere infraestructura

---

## 📝 Notas Técnicas

### **Estructura de Datos Actual:**
- `presupuesto_base`: Presupuesto inicial (1,289 registros)
- `ejecucion_presupuestaria`: Ejecuciones extraídas de boletines
- `metricas_gestion`: KPIs calculados
- `alertas_gestion`: Alertas automáticas

### **Formato de Archivos Excel Esperado:**
```
Columnas mínimas requeridas:
- ORGANISMO / JURISDICCION
- PROGRAMA
- PARTIDA / INCISO
- PRESUPUESTADO / CREDITO
- EJECUTADO / DEVENGADO
```

### **Mejoras Necesarias en Parser:**
- Detección de múltiples formatos de fecha
- Manejo de variantes de nombres de columnas
- Validación de datos antes de insertar
- Logging detallado de errores

---

**Preparado por:** Watcher Fiscal Agent  
**Última actualización:** Diciembre 2025  
**Próxima revisión:** Post-Fase 1

