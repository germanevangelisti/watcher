# 📊 Análisis de Precisión - Búsqueda Semántica

## Resultados del Benchmark

### Resumen General
```
Tests ejecutados: 6
Tests aprobados: 1/6 (16.7%) ❌
Precision@10 promedio: 13.3% ❌
Score promedio: 44.6%
Tiempo promedio: 380ms ✅
```

### Detalle por Test

| Test | Precisión@10 | Score Avg | Relevantes | Resultado |
|------|--------------|-----------|------------|-----------|
| Búsqueda genérica "contrato" | 0% | 26.3% | 0/10 | ❌ FALLÓ |
| Contratos de construcción | 0% | 43.2% | 0/10 | ❌ FALLÓ |
| Licitaciones públicas | 50% | 52.9% | 5/10 | ✅ PASÓ |
| Designaciones funcionarios | 30% | 50.0% | 3/10 | ❌ FALLÓ |
| Presupuesto/fondos | 0% | 49.9% | 0/10 | ❌ FALLÓ |
| Resoluciones administrativas | 0% | 45.0% | 0/10 | ❌ FALLÓ |

---

## Problemas Identificados

### 1. ⚠️ Baja Precisión General
**Problema**: Solo 13.3% de precision@10 promedio
**Causa**: El modelo actual (all-MiniLM-L6-v2) no está optimizado para:
- Documentos legales en español
- Terminología administrativa específica
- Texto formal gubernamental

### 2. ⚠️ Búsquedas Genéricas Fallan
**Problema**: "contrato" devuelve 0% de resultados relevantes
**Causa**: 
- Término demasiado genérico
- Falta de contexto semántico
- El modelo no captura bien términos aislados

### 3. ⚠️ Solo Queries Largas Funcionan
**Problema**: "licitación pública obras públicas" funciona (50%), pero queries cortas fallan
**Causa**: 
- El modelo necesita más contexto para entender la intención
- Búsquedas de 1-2 palabras son insuficientes

### 4. ✅ Velocidad Excelente
**Positivo**: 380ms promedio es muy bueno para producción

---

## Análisis de Modelo Actual

### Modelo: all-MiniLM-L6-v2
**Características**:
- **Dimensiones**: 384
- **Entrenamiento**: Inglés general
- **Velocidad**: Rápida ⚡
- **Precisión español**: Baja ❌
- **Contexto legal**: Ninguno ❌

### Limitaciones
1. No fue entrenado específicamente para español
2. No tiene conocimiento de terminología legal argentina
3. Embeddings de 384 dimensiones son limitados para texto especializado
4. No captura bien contexto administrativo/gubernamental

---

## Recomendaciones de Mejora

### Opción 1: Modelo Multilingüe (Implementable Ya) ⭐
**Modelo**: `paraphrase-multilingual-MiniLM-L12-v2`

**Ventajas**:
- ✅ Entrenado específicamente para español
- ✅ Mejor comprensión de contexto multilingüe
- ✅ Sin cambios en infraestructura
- ✅ Similar velocidad

**Implementación**:
```python
# En indexar_embeddings.py
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
embedding_function = lambda texts: model.encode(texts).tolist()

collection = client.get_or_create_collection(
    name="watcher_documents_multilingual",
    embedding_function=embedding_function
)
```

**Mejora esperada**: +20-30% en precision@10

### Opción 2: Modelo Legal Español (Óptimo) ⭐⭐⭐
**Modelo**: `nlpaueb/legal-bert-base-uncased` + fine-tuning

**Ventajas**:
- ✅ Pre-entrenado en textos legales
- ✅ Puede ser fine-tuned con boletines argentinos
- ✅ Mejor comprensión de terminología específica
- ⚠️ Requiere más recursos (768 dimensiones)

**Mejora esperada**: +40-50% en precision@10

### Opción 3: Modelo Embeddings Grande (Máxima Calidad) ⭐⭐⭐⭐
**Modelo**: `intfloat/multilingual-e5-large`

**Ventajas**:
- ✅ SOTA para tareas multilingües
- ✅ 1024 dimensiones (mucho más expresivo)
- ✅ Excelente para textos largos
- ⚠️ Más lento (2-3x)
- ⚠️ Requiere más espacio

**Mejora esperada**: +50-60% en precision@10

### Opción 4: Híbrido (Recomendado para Producción) ⭐⭐⭐⭐⭐
**Estrategia**: Combinar búsqueda semántica + keyword matching

**Implementación**:
1. **Búsqueda Semántica** con modelo multilingüe
2. **Re-ranking** con TF-IDF o BM25
3. **Filtros** por keywords exactas

**Código**:
```python
# 1. Búsqueda semántica (top 50)
semantic_results = await embedding_service.search(query, n_results=50)

# 2. Re-ranking con BM25
from rank_bm25 import BM25Okapi
corpus = [r['document'] for r in semantic_results]
bm25 = BM25Okapi(corpus)
scores = bm25.get_scores(query.split())

# 3. Combinar scores
final_results = []
for i, result in enumerate(semantic_results):
    combined_score = 0.7 * result['score'] + 0.3 * scores[i]
    result['combined_score'] = combined_score
    final_results.append(result)

# Ordenar por score combinado
final_results.sort(key=lambda x: x['combined_score'], reverse=True)
```

**Mejora esperada**: +30-40% en precision@10

---

## Plan de Acción Recomendado

### Fase 1: Quick Win (1-2 horas) ⭐
**Objetivo**: Mejorar precisión en 20-30%

1. **Re-indexar con modelo multilingüe**
```bash
# Instalar modelo
pip install sentence-transformers

# Re-indexar con nuevo modelo
python scripts/indexar_embeddings.py \
  --year 2026 \
  --model paraphrase-multilingual-MiniLM-L12-v2 \
  --force
```

2. **Actualizar búsqueda para usar nuevo modelo**
3. **Ejecutar benchmark nuevamente**

### Fase 2: Optimización (2-4 horas) ⭐⭐
**Objetivo**: +10-15% adicional

1. **Implementar re-ranking híbrido**
2. **Agregar boost por keywords exactas**
3. **Ajustar scores según tipo de documento**

### Fase 3: Fine-tuning (1-2 días) ⭐⭐⭐
**Objetivo**: Máxima precisión

1. **Crear dataset de training** con boletines etiquetados
2. **Fine-tune modelo multilingüe** con datos reales
3. **Evaluar y comparar**

---

## Métricas de Éxito

### Objetivos
```
Precision@10: > 60% (actualmente 13.3%)
Score promedio: > 65% (actualmente 44.6%)
Tiempo de respuesta: < 500ms (actualmente 380ms ✅)
```

### KPIs a Monitorear
- **Precision@K** (K=5, 10, 20)
- **Recall@K**
- **Mean Average Precision (MAP)**
- **Normalized Discounted Cumulative Gain (NDCG)**
- **Tiempo de respuesta**
- **Satisfacción del usuario** (feedback)

---

## Implementación Inmediata Sugerida

### Script de Re-indexación con Modelo Multilingüe
```python
# scripts/reindex_multilingual.py
import asyncio
from sentence_transformers import SentenceTransformer
import chromadb
from pathlib import Path

async def reindex_with_multilingual():
    # Cargar modelo multilingüe
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    # Crear nueva colección
    client = chromadb.PersistentClient(path=str(Path.home() / ".watcher" / "chromadb"))
    
    # Eliminar colección anterior
    try:
        client.delete_collection("watcher_documents")
    except:
        pass
    
    # Crear nueva con embedding function
    collection = client.create_collection(
        name="watcher_documents",
        metadata={"description": "Watcher Agent - Multilingual Model"},
        embedding_function=lambda texts: model.encode(texts).tolist()
    )
    
    print("✅ Colección creada con modelo multilingüe")
    print("📝 Ahora ejecuta: python scripts/indexar_embeddings.py --year 2026")

if __name__ == "__main__":
    asyncio.run(reindex_with_multilingual())
```

---

## Próximos Pasos

### Inmediato (Hoy)
1. ✅ Benchmark completado
2. ⏳ Decidir estrategia (modelo multilingüe o híbrido)
3. ⏳ Re-indexar con nuevo modelo
4. ⏳ Ejecutar nuevo benchmark

### Corto Plazo (Esta Semana)
1. Implementar re-ranking híbrido
2. Agregar más casos de prueba al benchmark
3. Crear dashboard de métricas

### Mediano Plazo (Próximas 2 Semanas)
1. Preparar dataset para fine-tuning
2. Experimentar con modelos especializados
3. A/B testing con usuarios reales

---

## Conclusión

**Estado Actual**: ❌ Precisión insuficiente para producción (13.3%)

**Problema Principal**: Modelo no optimizado para español legal

**Solución Recomendada**: 
1. **Inmediato**: Re-indexar con modelo multilingüe (+20-30%)
2. **Corto plazo**: Implementar búsqueda híbrida (+10-15% adicional)
3. **Mediano plazo**: Fine-tuning con datos reales (+10-20% adicional)

**Resultado Esperado**: >60% precision@10 (aceptable para producción)

---

**Archivo de resultados**: `scripts/benchmark_results.json`  
**Fecha de análisis**: 2026-02-09  
**Próxima evaluación**: Después de implementar modelo multilingüe
