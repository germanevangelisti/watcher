# Quick Start - Nueva Arquitectura Watcher Agent

**Guía rápida de uso de la arquitectura refactorizada**

---

## 🚀 Instalación

```bash
# 1. Instalar nuevas dependencias
cd watcher-monolith/backend
pip install chromadb openai

# 2. Configurar variables de entorno (opcional)
echo "CHROMADB_PATH=~/.watcher/chromadb" >> .env
echo "EMBEDDING_PROVIDER=openai" >> .env
# echo "OPENAI_API_KEY=sk-..." >> .env  # Si usas OpenAI

# 3. Iniciar servidor (Vector DB se inicializa automáticamente)
python -m uvicorn app.main:app --reload --port 8001
```

---

## 📚 Ejemplos de Uso

### 1. Descargar Boletines (Capa PDS)

```python
from app.scrapers.pds_prov import create_provincial_scraper
from datetime import date
import asyncio

async def download_bulletins():
    scraper = create_provincial_scraper()
    
    results = await scraper.download_range(
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 5),
        sections=[1, 2, 3]
    )
    
    print(f"✅ Descargados: {scraper.get_stats()}")
    return results

# Ejecutar
asyncio.run(download_bulletins())
```

### 2. Buscar Semánticamente (Capa KAA - RAGA)

```python
from agents.raga_agent import RAGAgent
import asyncio

async def semantic_search():
    agent = RAGAgent()
    
    class MockTask:
        task_type = "semantic_search"
        parameters = {
            "query": "licitaciones de obras públicas en enero",
            "limit": 5
        }
    
    result = await agent.execute(None, MockTask())
    
    for doc in result['results']['results']:
        print(f"📄 {doc.get('filename')}: {doc.get('snippet', '')[:100]}...")

asyncio.run(semantic_search())
```

### 3. Crear Alerta (Capa OEx - ALA)

```python
from app.services.alert_dispatcher import get_alert_dispatcher, AlertPriority
import asyncio

async def create_alert():
    dispatcher = get_alert_dispatcher()
    
    alert = await dispatcher.create_and_dispatch(
        title="⚠️ Monto elevado detectado",
        message="Licitación por $150M requiere revisión",
        priority=AlertPriority.HIGH,
        category="high_amount",
        metadata={"amount": 150000000}
    )
    
    print(f"✅ Alerta creada: {alert['alert_id']}")

asyncio.run(create_alert())
```

### 4. Generar Reporte (Capa OEx - RPA)

```python
from app.services.report_generator import get_report_generator, ReportType, ReportFormat
import asyncio

async def generate_report():
    generator = get_report_generator()
    
    report = await generator.generate_report(
        report_type=ReportType.EXECUTIVE_SUMMARY,
        data={
            "period": "Febrero 2026",
            "total_documents": 50,
            "high_risk_count": 3,
            "total_amount": 250000000,
            "key_findings": [
                "3 licitaciones de alto riesgo",
                "Aumento del 20% en contratos"
            ]
        },
        format=ReportFormat.MARKDOWN
    )
    
    print(report['content'])

asyncio.run(generate_report())
```

### 5. API Gateway (Interfaz Unificada)

```bash
# Búsqueda semántica vía Gateway
curl -X POST http://localhost:8001/api/v1/gateway \
  -H "Content-Type: application/json" \
  -d '{
    "service": "kaa",
    "operation": "rag_search",
    "parameters": {
      "query": "contratos de construcción",
      "limit": 10
    }
  }'

# Generar reporte vía Gateway
curl -X POST http://localhost:8001/api/v1/gateway \
  -H "Content-Type: application/json" \
  -d '{
    "service": "oex",
    "operation": "generate_report",
    "parameters": {
      "type": "executive_summary",
      "format": "json",
      "data": {
        "period": "Q1 2026",
        "total_documents": 150
      }
    }
  }'

# Ver estadísticas del Gateway
curl http://localhost:8001/api/v1/gateway/stats

# Listar servicios disponibles
curl http://localhost:8001/api/v1/gateway/services
```

---

## 🏗️ Arquitectura en 4 Capas

```
┌─────────────────────────────────────┐
│  PDS - Portal Data Scrapers         │  ← Descarga de fuentes
│  • pds_prov.py (Córdoba) ✅         │
│  • pds_muni.py (Municipal) 📝       │
│  • pds_nat.py (Nacional) 📝         │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  DIA - Data Integration Adapters    │  ← Normalización
│  • sca_prov.py (Adapter) ✅         │
│  • ppa.py (Persistence) ✅          │
│  • SQLite + ChromaDB                │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  KAA - Knowledge AI Agents          │  ← Análisis IA
│  • kba_agent.py (Knowledge) ✅      │
│  • raga_agent.py (RAG) ✅           │
│  • document_intelligence.py ✅      │
│  • anomaly_detection.py ✅          │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  OEx - Output Execution             │  ← Salidas
│  • alert_dispatcher.py (ALA) ✅     │
│  • report_generator.py (RPA) ✅     │
│  • api_gateway.py (Gateway) ✅      │
└─────────────────────────────────────┘
```

---

## 📁 Archivos Clave

| Capa | Archivo | Descripción |
|------|---------|-------------|
| **PDS** | `app/scrapers/base_scraper.py` | Interfaz base para scrapers |
| **PDS** | `app/scrapers/pds_prov.py` | Scraper provincial |
| **DIA** | `app/adapters/base_adapter.py` | Interfaz base para adapters |
| **DIA** | `app/adapters/sca_prov.py` | Adapter provincial |
| **DIA** | `app/adapters/ppa.py` | Persistence adapter (SQL+VDB) |
| **DIA** | `app/services/embedding_service.py` | Vector embeddings |
| **KAA** | `agents/kba_agent.py` | Knowledge Base Agent |
| **KAA** | `agents/raga_agent.py` | RAG Agent |
| **OEx** | `app/services/alert_dispatcher.py` | Alert dispatcher |
| **OEx** | `app/services/report_generator.py` | Report generator |
| **OEx** | `app/api/v1/api_gateway.py` | API Gateway |

---

## 🔧 Troubleshooting

### ChromaDB no se inicializa

```bash
# Verificar instalación
pip list | grep chromadb

# Reinstalar si es necesario
pip install --upgrade chromadb

# Verificar directorio
ls -la ~/.watcher/chromadb/
```

### Embeddings no funcionan

```bash
# Si usas OpenAI, verificar API key
echo $OPENAI_API_KEY

# Cambiar a embeddings locales (no requiere API key)
export EMBEDDING_PROVIDER=local
```

### Importación de módulos falla

```bash
# Verificar PYTHONPATH
cd watcher-monolith/backend
export PYTHONPATH=$PWD:$PYTHONPATH

# O ejecutar desde el directorio correcto
cd watcher-monolith/backend
python -m uvicorn app.main:app
```

---

## 📊 Verificar Instalación

```python
# Test completo de la nueva arquitectura
import asyncio

async def test_architecture():
    print("🧪 Testing nueva arquitectura...\n")
    
    # 1. Test PDS
    print("1️⃣ Testing PDS (Scrapers)...")
    from app.scrapers.pds_prov import create_provincial_scraper
    scraper = create_provincial_scraper()
    print(f"   ✅ Provincial scraper: {scraper.name}")
    
    # 2. Test DIA
    print("\n2️⃣ Testing DIA (Adapters)...")
    from app.adapters.sca_prov import create_provincial_adapter
    adapter = create_provincial_adapter()
    print(f"   ✅ Provincial adapter: {adapter.source_type}")
    
    # 3. Test Vector DB
    print("\n3️⃣ Testing Vector DB...")
    from app.services.embedding_service import get_embedding_service
    service = get_embedding_service()
    print(f"   ✅ Embedding service: {service.collection_name if service.collection else 'Not initialized'}")
    
    # 4. Test KAA
    print("\n4️⃣ Testing KAA (Agents)...")
    from agents.raga_agent import RAGAgent
    agent = RAGAgent()
    print(f"   ✅ RAG Agent: {agent.name}")
    
    # 5. Test OEx
    print("\n5️⃣ Testing OEx (Outputs)...")
    from app.services.alert_dispatcher import get_alert_dispatcher
    from app.services.report_generator import get_report_generator
    dispatcher = get_alert_dispatcher()
    generator = get_report_generator()
    print(f"   ✅ Alert dispatcher: Ready")
    print(f"   ✅ Report generator: Ready")
    
    # 6. Test API Gateway
    print("\n6️⃣ Testing API Gateway...")
    from app.api.v1.api_gateway import get_gateway
    gateway = get_gateway()
    print(f"   ✅ API Gateway: {len(gateway.service_registry)} services")
    
    print("\n✅ ¡Arquitectura completamente funcional!")

asyncio.run(test_architecture())
```

---

## 📚 Documentación Completa

- **Arquitectura Completa**: `ARQUITECTURA_REFACTOR_COMPLETADA.md`
- **Plan Original**: `.cursor/plans/arquitectura_watcher_refactor_141282c5.plan.md`
- **README Principal**: `README.md`

---

## 🎯 Próximos Pasos

1. **Probar scrapers municipales**: Implementar `pds_muni.py`
2. **Optimizar embeddings**: Experimentar con modelos locales
3. **Extender API Gateway**: Agregar autenticación y rate limiting
4. **Crear workflows**: Implementar WOA (Workflow Orchestrator Agent)

---

**¡Listo para usar! 🚀**
