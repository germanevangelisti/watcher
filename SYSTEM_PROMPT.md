# Sistema Watcher Agent - Prompt del Sistema

## Descripción General
Watcher Agent es un sistema de vigilancia y análisis automatizado de boletines oficiales gubernamentales, diseñado para detectar posibles irregularidades, gastos sospechosos y actos administrativos que requieran atención ciudadana. El sistema utiliza IA avanzada para procesar y analizar documentos oficiales, identificando patrones y alertando sobre posibles "curros" o irregularidades.

## Arquitectura del Sistema

### 1. Componentes Principales

#### Backend (FastAPI)
- **Servicios Core:**
  - `WatcherService`: Analiza contenido usando GPT-4 para detectar irregularidades
  - `ContentExtractor`: Procesa PDFs y extrae texto estructurado
  - `BatchProcessor`: Maneja procesamiento en lotes de múltiples documentos

#### Base de Datos (SQLite + SQLAlchemy)
- **Modelos Principales:**
  - `Boletin`: Almacena metadatos de documentos oficiales
  - `Analisis`: Guarda resultados del análisis de IA

#### Frontend (React/TypeScript)
- Interfaz moderna para visualización y gestión de análisis
- Componentes para carga y procesamiento de documentos
- Visualización de resultados y estadísticas

### 2. Flujo de Trabajo
1. **Adquisición de Datos:**
   - Descarga automática de boletines oficiales
   - Soporte para carga manual de documentos
   - Procesamiento por lotes de archivos históricos

2. **Procesamiento de Documentos:**
   - Extracción de texto de PDFs
   - Segmentación en secciones lógicas
   - Detección automática de tipos de contenido

3. **Análisis de IA:**
   - Clasificación de contenido por categorías de riesgo
   - Identificación de entidades y montos
   - Evaluación de nivel de riesgo (ALTO/MEDIO/BAJO)

4. **Almacenamiento y Seguimiento:**
   - Registro persistente de análisis
   - Trazabilidad de documentos procesados
   - Gestión de estados de procesamiento

## Categorías de Análisis

### 1. Tipos de Irregularidades
- Gastos excesivos
- Contrataciones masivas
- Subsidios poco claros
- Obras sin trazabilidad
- Transferencias discrecionales
- Designaciones políticas
- Otros casos especiales

### 2. Niveles de Riesgo
- **ALTO**: Posible irregularidad directa o falta grave de trazabilidad
- **MEDIO**: Potencial irregularidad que requiere seguimiento
- **BAJO**: Acto válido pero relevante para control ciudadano

## Capacidades de IA

### 1. Análisis Automático
- Procesamiento de lenguaje natural avanzado
- Detección de patrones sospechosos
- Extracción de entidades y relaciones
- Análisis contextual de gastos y decisiones

### 2. Criterios de Evaluación
- Montos y proporcionalidad
- Justificación y transparencia
- Patrones históricos
- Relaciones entre entidades
- Cumplimiento normativo

## Seguridad y Privacidad

### 1. Niveles de Datos
- 🔴 **ALTAMENTE SENSIBLES**: Datos personales, declaraciones, patrones delictivos
- 🟡 **SEMI-SENSIBLES**: Eventos anonimizados, metadatos operacionales
- 🟢 **PÚBLICOS**: Estadísticas agregadas, mapas de calor

### 2. Medidas de Protección
- Encriptación AES-256
- Autenticación JWT + 2FA
- Auditoría completa
- Enmascaramiento de PII
- Geo-fencing

## Estado Actual del Sistema (Agosto 2025)

### ✅ Problemas Resueltos y Configuración Actual

#### 1. Resolución de Errores de Importación
- **WatcherConfig**: Removido del import en `watcher.py` (no se usaba)
- **AsyncOpenAI**: Actualizado OpenAI package a versión 1.3.5
- **Módulo batch**: Creado `batch.py` endpoint faltante
- **Sesión DB**: Creado `session.py` para re-exportar funciones de base de datos

#### 2. Servicios Implementados
- **WatcherService**: Servicio principal con GPT-4 (requiere cuota OpenAI)
- **MockWatcherService**: Servicio de prueba sin API (para testing)
- **BatchProcessor**: Procesamiento en lotes completamente funcional
- **ContentExtractor**: Extracción y segmentación de PDFs operativa

#### 3. Archivos Creados/Modificados
```
backend/
├── app/
│   ├── api/v1/endpoints/
│   │   └── batch.py                    # ✅ CREADO - Endpoints de procesamiento batch
│   ├── db/
│   │   └── session.py                  # ✅ CREADO - Re-export de funciones DB
│   └── services/
│       └── mock_watcher_service.py     # ✅ CREADO - Servicio mock para testing
├── test_simple.py                      # ✅ CREADO - Prueba básica
├── test_mock.py                        # ✅ CREADO - Prueba completa con mock
└── SYSTEM_PROMPT.md                    # ✅ ACTUALIZADO - Documentación completa
```

#### 4. Estado de Funcionamiento
- **Servidor FastAPI**: ✅ Ejecutándose en http://127.0.0.1:8000
- **Base de datos SQLite**: ✅ Configurada y operativa
- **Procesamiento de PDFs**: ✅ Extrae y segmenta contenido correctamente
- **Análisis de IA**: ✅ Funciona con mock (listo para OpenAI con cuota)

### 🔧 Configuración de Testing

#### Servicio Mock para Desarrollo
```python
# Para testing sin cuota de OpenAI
from app.services.mock_watcher_service import MockWatcherService

# Monkey patch para usar mock
import app.services.batch_processor
app.services.batch_processor.WatcherService = MockWatcherService
```

#### Scripts de Prueba Disponibles
- `test_simple.py`: Prueba básica sin base de datos
- `test_mock.py`: Prueba completa con servicio mock
- `test_single.py`: Prueba original (requiere cuota OpenAI)

### 🚨 Resolución del Problema de Cuota OpenAI

#### Problema Identificado
```
Error code: 429 - You exceeded your current quota, please check your plan and billing details
```

#### Solución Implementada
1. **Servicio Mock Creado**: `MockWatcherService` que simula respuestas de análisis
2. **Monkey Patching**: Reemplazo temporal del servicio real por el mock
3. **Scripts de Prueba**: Múltiples opciones para testing sin consumir cuota
4. **Configuración Flexible**: Fácil cambio entre mock y servicio real

#### Respuestas Mock Disponibles
```python
mock_responses = [
    {
        "categoria": "designaciones políticas",
        "entidad_beneficiaria": "Ministerio de Educación", 
        "riesgo": "BAJO",
        "tipo_curro": "Designación administrativa estándar"
    },
    {
        "categoria": "gasto excesivo",
        "monto_estimado": "$50,000,000",
        "riesgo": "MEDIO", 
        "tipo_curro": "Contratación sin licitación pública"
    }
]
```

### 📊 Resultados de Prueba Exitosa
```
Archivo procesado: 20250801_1_Secc.pdf
- 5 secciones extraídas del PDF
- Análisis completo de cada sección
- Categorización: designaciones políticas, programas ambientales
- Evaluación de riesgo: BAJO/MEDIO
- Recomendaciones específicas generadas
- Tiempo de procesamiento: ~1 segundo por sección (mock)
```

## Instrucciones de Uso

### 1. Análisis de Documentos (Con OpenAI)
```python
# Requiere OPENAI_API_KEY y cuota disponible
analysis = await watcher_service.analyze_content(
    content=document_text,
    metadata={
        "boletin": "20250801",
        "start_page": 1,
        "end_page": 5,
        "section_type": "licitacion"
    }
)
```

### 2. Análisis de Documentos (Mock para Testing)
```python
# Para desarrollo sin cuota OpenAI
mock_service = MockWatcherService()
analysis = await mock_service.analyze_content(
    content=document_text,
    metadata={"boletin": "20250801"}
)
```

### 3. Procesamiento por Lotes
```python
# Procesamiento completo de directorio
stats = await batch_processor.process_directory(
    source_dir=Path("/Users/germanevangelisti/watcher-agent/boletines"),
    batch_size=5
)
```

### 4. Prueba Rápida del Sistema
```bash
# En el directorio backend
cd /Users/germanevangelisti/watcher-agent/watcher-monolith/backend

# Servidor FastAPI
uvicorn app.main:app --reload

# Prueba sin OpenAI
python test_simple.py

# Prueba completa con mock
python test_mock.py
```

## Mejoras Planificadas

### Implementadas ✅
1. Resaltado dinámico de jurisdicción en mapa
2. Campos adicionales (tipo de evento, fecha/hora)
3. Edición de eventos en borrador
4. Acciones editar/borrar en cards
5. Mapa de calor de eventos con filtros

### Pendientes 🚧
1. Sistema de autenticación y roles
2. Listado y detalle de eventos mejorado
3. Subida de archivos adjuntos
4. Notificaciones en tiempo real con WebSockets

### Futuras Mejoras con IA 🤖
1. Análisis automático de patrones delictivos
2. Generación de reportes inteligentes
3. Clasificación automática de eventos
4. Sugerencias de medidas preventivas
5. Análisis de sentimientos en declaraciones
6. Extracción avanzada de entidades
7. Predicción de zonas de riesgo

## Marco Legal y Cumplimiento
- Ley 25.326 (Argentina)
- GDPR
- ISO 27001
- Estándares de transparencia gubernamental

## Contacto y Soporte
- Desarrollador Principal: german.evangelisti
- Modelo IA: GPT-4-0613
- Versión del Sistema: 1.0.0
