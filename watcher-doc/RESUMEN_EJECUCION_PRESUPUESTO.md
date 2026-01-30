# 📊 Resumen Ejecutivo: Próximos Pasos para Ejecución del Presupuesto

## 🎯 Estado Actual

### ✅ **Completado**
- **Presupuesto Base 2025:** 1,289 programas cargados
- **Ejecución Baseline Marzo 2025:** 4 archivos Excel procesados
- **Infraestructura:** Sistema de BD y APIs listos

### ⚠️ **Pendiente**
- **Datos actualizados:** Solo hasta marzo 2025
- **Boletines procesados:** 5 de 99 (5%)
- **Ejecuciones detectadas:** Limitadas

---

## 🚀 Acciones Inmediatas (Prioridad Alta)

### **1. Obtener Archivos Excel Actualizados** 🔴

**Objetivo:** Datos de ejecución más recientes (abril-diciembre 2025)

**Fuentes a consultar:**
- Portal de Datos Abiertos Córdoba: `https://datosabiertos.cba.gov.ar/`
- Ministerio de Economía y Gestión Pública
- Dirección de Presupuesto

**Archivos necesarios:**
```
- Gastos Administración Central - Acumulado [Período] 2025.xlsx
- Gastos EMAEE - Acumulado [Período] 2025.xlsx
- Recursos Administración Central - Acumulado [Período] 2025.xlsx
- Recursos EMAEE - Acumulado [Período] 2025.xlsx
```

**Comando para procesar:**
```bash
cd watcher-monolith/backend
python scripts/parse_excel_presupuesto.py
python scripts/populate_budget.py
```

---

### **2. Procesar Todos los Boletines** 🔴

**Objetivo:** Extraer ejecuciones de los 99 boletines disponibles

**Comando:**
```bash
cd watcher-monolith/backend
# Procesar todos los boletines (sin --test)
python scripts/process_boletines_actos.py

# O usar el batch processor
python -m app.services.batch_processor
```

**Resultado esperado:**
- ~180+ actos administrativos extraídos
- Ejecuciones presupuestarias detectadas
- Vinculación con programas

---

### **3. Mejorar Vinculación** 🟡

**Problema actual:** Solo 44.4% de actos vinculados

**Mejoras necesarias:**
- Detección de partidas presupuestarias en texto
- Matching semántico mejorado
- Uso de embeddings para matching

**Scripts a mejorar:**
- `app/services/acto_parser.py` - Agregar detección de partidas
- `app/services/semantic_matcher.py` - Mejorar scoring

---

## 📋 Plan de Acción por Semana

### **Semana 1: Datos Actualizados**
- [ ] Buscar y descargar archivos Excel más recientes
- [ ] Procesar y cargar en BD
- [ ] Validar datos

### **Semana 2: Procesamiento Completo**
- [ ] Ejecutar procesamiento de 99 boletines
- [ ] Extraer todas las ejecuciones
- [ ] Validar calidad

### **Semana 3: Mejoras**
- [ ] Mejorar detección de partidas
- [ ] Aumentar tasa de vinculación a >80%
- [ ] Implementar alertas de desvíos

### **Semana 4: Dashboard**
- [ ] Métricas de ejecución en dashboard
- [ ] Gráficos de comparación
- [ ] Alertas visibles

---

## 🔍 Fuentes de Datos

1. **Portal Datos Abiertos:** `https://datosabiertos.cba.gov.ar/`
2. **Ministerio de Economía:** Dirección de Presupuesto
3. **Boletines Oficiales:** 99 boletines disponibles en `/boletines/`
4. **Portal Transparencia:** Informes de gestión

---

## 📊 Métricas de Éxito

- ✅ Datos actualizados hasta período más reciente
- ✅ 99 boletines procesados
- ✅ >150 actos extraídos
- ✅ Tasa de vinculación >70%

---

**Ver documento completo:** `ANALISIS_EJECUCION_PRESUPUESTO.md`

