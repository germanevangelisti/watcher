# 🎉 Nuevas Funcionalidades UI - Watcher Agent

## Resumen

Se han implementado **2 nuevas páginas** en la interfaz de usuario para visualizar y explorar los datos procesados:

1. **🔍 Búsqueda Semántica** (`/search`)
2. **🕸️ Grafo de Conocimiento** (`/knowledge-graph`)

---

## 1. Búsqueda Semántica

### Ubicación
- **URL**: `http://localhost:5173/search`
- **Navegación**: Menú principal → "Búsqueda"

### Características

#### Búsqueda Inteligente
- Búsqueda semántica usando embeddings en ChromaDB
- Encuentra contenido por significado, no solo palabras exactas
- Resultados ordenados por relevancia (score 0-100%)

#### Filtros Avanzados
- **Año**: Filtrar por año (2024, 2025, 2026)
- **Mes**: Filtrar por mes específico
- **Sección**: Filtrar por sección del boletín (1-5)
- **Cantidad de resultados**: 5-50 resultados

#### Visualización de Resultados
Para cada resultado se muestra:
- 📄 **Nombre del documento** (`20260203_1_Secc.pdf`)
- 📊 **Score de relevancia** (badge con color según relevancia)
- 📅 **Fecha** del boletín
- 📍 **Sección** del boletín
- 📝 **ID del chunk** (fragmento específico)
- 📖 **Fragmento de texto** con highlights de términos buscados
- 🔗 **Botón para ver documento completo**

#### Acceso al Texto Original
- Click en el icono 🔗 para abrir modal con texto completo del documento
- Scroll infinito para navegar documentos largos
- Opción de descargar el archivo `.txt`

### Ejemplo de Uso

```
Búsqueda: "contratos de construcción de obras públicas"

Resultados (10 encontrados en 234ms):
┌─────────────────────────────────────────────────────────┐
│ 📄 20260203_2_Secc.pdf              [92% relevancia]   │
│ 📅 2026-02-03  📍 Sección 2                            │
│                                                         │
│ "...DECRETO Nº 123/2026. Por el presente se aprueba   │
│  la licitación pública para la construcción de obras   │
│  en la Ruta Provincial 35..."                          │
│                                              [Ver doc 🔗]│
└─────────────────────────────────────────────────────────┘
```

---

## 2. Grafo de Conocimiento

### Ubicación
- **URL**: `http://localhost:5173/knowledge-graph`
- **Navegación**: Menú principal → "Grafo"

### Características

#### Visualización del Grafo
- **Canvas interactivo** con visualización de entidades y relaciones
- **Algoritmo force-directed** para layout automático
- **Nodos coloreados** por tipo de entidad:
  - 🔵 Persona (azul)
  - 🟢 Organismo (verde)
  - 🔴 Empresa (rojo)
  - 🟡 Contrato (amarillo)
  - 🟣 Monto (violeta)
- **Tamaño de nodo** proporcional a cantidad de menciones
- **Enlaces** representan relaciones (contrata, designa, adjudica)
- **Transparencia del enlace** según confianza de la relación

#### Filtros
- **Máximo de nodos**: 10-200 (default: 50)
- **Mínimo de menciones**: 1-20 (default: 3)
- Botón "Actualizar" para recargar el grafo

#### Tabs de Navegación

##### 📊 Tab "Visualización"
- Grafo interactivo completo
- Estadísticas del grafo:
  - Total de nodos
  - Total de enlaces
  - Leyenda de colores

##### 👤 Tab "Entidades"
Tabla con todas las entidades del sistema:
- **Tipo** (con icono y badge)
- **Nombre** de la entidad
- **Total de menciones**
- **Primera aparición** (fecha)
- **Última aparición** (fecha)
- **Botón de acción** → Ver historial completo

##### ⚠️ Tab "Patrones Sospechosos"
Lista de patrones detectados por el Historical Intelligence Agent:
- **Nombre del patrón** (ej: "Contratos repetitivos", "Designaciones irregulares")
- **Severidad**: critical, high, medium, low
- **Descripción** del patrón
- **Entidades involucradas** (primeras 5 + contador)
- **Estadísticas**: total de casos, periodo

#### Modal de Historial de Entidad
Al hacer click en "Ver historial" de una entidad:
- **Tipo y metadata** de la entidad
- **Total de documentos** donde aparece
- **Total de relaciones** con otras entidades
- **Periodo de actividad** (fecha inicio - fin)
- **Patrones sospechosos** detectados (si hay)
- **Timeline de eventos**: lista cronológica de todas las apariciones con:
  - Fecha
  - Nombre del boletín
  - Contexto (snippet del texto donde aparece)

---

## Arquitectura Técnica

### Backend

#### Nuevos Endpoints

**Búsqueda Semántica**
```
POST /api/v1/search/semantic
GET  /api/v1/search/stats
GET  /api/v1/documentos/text/{filename}
GET  /api/v1/documentos/text/{filename}/download
GET  /api/v1/documentos/pdf/{filename}
```

**Grafo de Conocimiento**
```
GET /api/v1/entidades/graph
GET /api/v1/entidades/
GET /api/v1/entidades/{id}
GET /api/v1/entidades/{id}/timeline
GET /api/v1/entidades/{id}/relaciones
GET /api/v1/entidades/{id}/history
GET /api/v1/entidades/patterns
```

#### Servicios Utilizados
- **EmbeddingService**: Búsqueda en ChromaDB
- **EntityService**: Extracción y normalización de entidades
- **HistoricalIntelligenceAgent**: Análisis de patrones y timeline

### Frontend

#### Nuevos Componentes
- `SearchPage.tsx` - Página de búsqueda semántica
- `KnowledgeGraphPage.tsx` - Página del grafo

#### Nuevos Tipos
- `types/search.ts` - Tipos TypeScript para búsqueda y grafo

#### Funcionalidades Mantine UI
- TextInput con iconos
- Filtros con Select y NumberInput
- Cards y Badges para resultados
- Modal para documento completo
- Canvas para visualización del grafo
- Tabs para navegación
- Table para lista de entidades
- ScrollArea para contenido largo

---

## Flujo Completo del Usuario

### Escenario: Investigar contratos de construcción

1. **Búsqueda Inicial**
   - Ir a `/search`
   - Buscar: "contratos construcción obras públicas"
   - Ver 10 resultados relevantes
   - Click en 🔗 del resultado más relevante
   - Leer contexto completo del documento

2. **Explorar Entidades**
   - Ir a `/knowledge-graph`
   - Tab "Entidades"
   - Buscar en tabla: "Ministerio de Obras Públicas"
   - Click en "Ver historial"
   - Ver timeline completo de actividad
   - Identificar patrones sospechosos

3. **Visualizar Relaciones**
   - Tab "Visualización"
   - Ajustar filtros: max 100 nodos, min 5 menciones
   - Observar el grafo
   - Identificar clusters de entidades relacionadas
   - Detectar empresas con múltiples contratos

4. **Revisar Patrones**
   - Tab "Patrones Sospechosos"
   - Ver patrón "Contratos repetitivos"
   - Revisar entidades involucradas
   - Ver periodo y cantidad de casos

---

## Comandos para Iniciar

### Backend
```bash
cd /Users/germanevangelisti/watcher-agent/watcher-monolith/backend
python -m uvicorn app.main:app --reload --port 8001
```

### Frontend
```bash
cd /Users/germanevangelisti/watcher-agent/watcher-monolith/frontend
npm run dev
```

### Acceso
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

---

## Próximos Pasos Recomendados

1. **Mejorar Visualización del Grafo**
   - Agregar zoom y pan al canvas
   - Implementar drag & drop de nodos
   - Tooltip al hover sobre nodos/enlaces
   - Opciones de layout (circular, jerárquico, force-directed)

2. **Funcionalidades Avanzadas de Búsqueda**
   - Búsqueda por rangos de fecha
   - Guardar búsquedas frecuentes
   - Exportar resultados a CSV/PDF
   - Búsqueda de entidades específicas

3. **Grafo Mejorado**
   - Usar librería especializada (vis.js, cytoscape.js, react-force-graph)
   - Filtrar por tipo de relación
   - Expandir/colapsar subgrafos
   - Búsqueda en el grafo
   - Destacar caminos entre entidades

4. **Integración**
   - Link desde Alertas → Búsqueda
   - Link desde Documentos → Entidades del documento
   - Link desde Dashboard → Top entidades en grafo

---

## Datos de Ejemplo Disponibles

Según los scripts ejecutados, deberías tener:
- ✅ **5 boletines indexados** (2026-02-03)
- ✅ **499 chunks** en ChromaDB
- ✅ Entidades extraídas y persistidas
- ✅ Relaciones detectadas entre entidades

¡Ahora puedes explorar todo esto visualmente en la UI! 🎉
