# 🚀 Quick Start - Watcher DS Lab

## ✅ Sistema Listo Para Usar

Tu sistema DS Lab está **100% operativo** con:
- ✅ 1,063 documentos registrados
- ✅ Base de datos configurada
- ✅ Backend corriendo (puerto 8001)
- ✅ Frontend corriendo (puerto 3001)

---

## 🎯 Cómo Usar el Sistema Ahora Mismo

### 1️⃣ Abrir la UI de Análisis

```
http://localhost:3001/dslab/analysis
```

### 2️⃣ Configurar tu Análisis

En la pestaña **"Configurar Análisis"**:
- **Config**: Selecciona `watcher_baseline v1.0.0`
- **Fecha inicio**: `2025-01-01`
- **Fecha fin**: `2025-01-31`
- **Secciones**: Deja todas seleccionadas
- Click **"Iniciar Análisis"**

### 3️⃣ Ver Progreso en Tiempo Real

Automáticamente verás:
- 📊 Barra de progreso animada
- 📈 Métricas actualizándose cada 2 segundos
- 📄 Documento actual que se está procesando
- ⏱️ Tiempo estimado restante
- 📝 Logs en el panel derecho

### 4️⃣ Ver Resultados

Cuando termine (automático):
- 📊 Score de transparencia promedio
- 🚨 Red flags detectadas
- 📈 Distribución de riesgo
- 🔍 Detalles por severidad

---

## 📊 Análisis Rápido de Prueba

Si quieres probar con pocos documentos primero:

```bash
cd /Users/germanevangelisti/watcher-agent/watcher-monolith/backend
python scripts/run_test_analysis.py
```

Esto analizará 10 documentos de enero en ~30 segundos.

---

## 🗂️ Ver Calendario de Cobertura

```
http://localhost:3001/dslab
```

Verás:
- **Vista General**: Todos los meses del año
- **Calendario**: Día por día de cada mes
- **Descargas**: Para descargar meses faltantes

---

## 📈 Datos Actuales

```
📄 Total documentos: 1,063 boletines
📅 Meses cubiertos: 11 de 12 (Ene-Nov 2025)

Distribución:
- Enero: 108 docs
- Febrero: 99 docs
- Marzo: 88 docs
- Abril: 95 docs
- Mayo: 100 docs
- Junio: 94 docs
- Julio: 107 docs
- Agosto: 99 docs
- Septiembre: 110 docs
- Octubre: 110 docs
- Noviembre: 53 docs
```

---

## 🎛️ Opciones de Análisis

### Análisis de 1 Mes (Recomendado para empezar)
```
Inicio: 2025-01-01
Fin: 2025-01-31
Docs: ~108
Tiempo: ~6 minutos
```

### Análisis de 3 Meses
```
Inicio: 2025-01-01
Fin: 2025-03-31
Docs: ~295
Tiempo: ~15 minutos
```

### Análisis Completo (Todo el año)
```
Inicio: 2025-01-01
Fin: 2025-11-30
Docs: 1,063
Tiempo: ~55 minutos
```

---

## 🔍 Qué Busca el Análisis

El sistema detecta automáticamente:

### 🚨 Red Flags Críticas
- **HIGH_AMOUNT**: Montos superiores a $50M
- **MISSING_BENEFICIARY**: Falta identificación de beneficiario
- **LOW_TRANSPARENCY**: Score menor a 30/100

### ⚠️ Red Flags Medias
- **SUSPICIOUS_PATTERN**: Patrones inusuales en texto
- **REPEATED_BENEFICIARY**: Mismo beneficiario múltiples veces

### Métricas Calculadas
- **Transparency Score** (0-100): Mayor = más transparente
- **Risk Level** (low/medium/high): Nivel de riesgo del documento
- **Anomaly Score** (0-1): Probabilidad de anomalía

---

## 📝 Después del Análisis

Los resultados se guardan en la base de datos para:
- ✅ Ver histórico de análisis
- ✅ Comparar diferentes configuraciones
- ✅ Exportar reportes (próximamente)
- ✅ Identificar tendencias temporales

Accede a resultados via API:
```bash
curl http://localhost:8001/api/v1/dslab/analysis/executions | python -m json.tool
```

---

## 🆘 Si Algo Sale Mal

### Error: UI no carga
```bash
cd /Users/germanevangelisti/watcher-agent/watcher-monolith/frontend
npm run dev
```

### Error: Backend no responde
```bash
cd /Users/germanevangelisti/watcher-agent/watcher-monolith/backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Error: "Table not found"
```bash
cd /Users/germanevangelisti/watcher-agent/watcher-monolith/backend
python scripts/create_dslab_tables.py
python scripts/register_existing_boletines.py
python scripts/create_initial_config.py
```

📖 **Guía completa**: `/Users/germanevangelisti/watcher-agent/docs/DSLAB_TROUBLESHOOTING.md`

---

## 📚 Documentación Completa

- **Guía de Uso**: `/Users/germanevangelisti/watcher-agent/docs/DSLAB_GUIA_USO_COMPLETA.md`
- **UI de Análisis**: `/Users/germanevangelisti/watcher-agent/docs/DSLAB_UI_ANALISIS_GUIA.md`
- **Troubleshooting**: `/Users/germanevangelisti/watcher-agent/docs/DSLAB_TROUBLESHOOTING.md`
- **Sistema Completo**: `/Users/germanevangelisti/watcher-agent/SISTEMA_DSLAB_COMPLETO.md`
- **Deployment**: `/Users/germanevangelisti/watcher-agent/DSLAB_DEPLOYMENT_SUCCESS.md`

---

## 🎯 Siguiente Paso Recomendado

**Ejecuta tu primer análisis real:**

1. Abre http://localhost:3001/dslab/analysis
2. Configura enero completo (2025-01-01 a 2025-01-31)
3. Click "Iniciar Análisis"
4. Observa el progreso en tiempo real
5. Revisa los resultados cuando termine

**Tiempo estimado**: ~6 minutos para 108 documentos

---

**¡El sistema está listo! 🚀**

¿Preguntas? Revisa la documentación o ejecuta un análisis de prueba primero.

