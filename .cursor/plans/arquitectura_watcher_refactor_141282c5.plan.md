---
name: Arquitectura Watcher Refactor
overview: Análisis comparativo entre la arquitectura propuesta (imagen whiteboard) y la implementación actual del repositorio, identificando gaps y proponiendo una ruta de refactorización incremental hacia un sistema multi-fuente con agentes IA especializados.
todos:
  - id: fase1-scrapers
    content: "Abstraer capa de extraccion: crear base_scraper.py y migrar downloader a pds_prov.py"
    status: completed
  - id: fase2-adapters
    content: "Implementar adaptadores DIA: base_adapter.py, sca_prov.py, ppa.py"
    status: completed
    dependencies:
      - fase1-scrapers
  - id: fase3-vectordb
    content: Integrar Vector Database (ChromaDB) y embedding_service.py
    status: completed
    dependencies:
      - fase2-adapters
  - id: fase4-agents
    content: "Especializar agentes: kba_agent.py, raga_agent.py, potenciar document_intelligence"
    status: completed
    dependencies:
      - fase3-vectordb
  - id: fase5-outputs
    content: "Separar outputs: alert_dispatcher.py, report_generator.py, API Gateway pattern"
    status: completed
    dependencies:
      - fase4-agents
---

# Arquitectura Watcher - Analisis Comparativo y Plan de Refactor

## Interpretacion de la Arquitectura Propuesta (Imagen)

La imagen muestra una arquitectura en **4 capas** diseñada para escalar a multiples fuentes de datos:

```mermaid
flowchart TB
    subgraph PDS [PDS - Portal Data Scrapers]
        PDS_MUNI["PDS-MUNI<br/>DOC, PRES, ETEL, OBRAS, CONTRAT"]
        PDS_PROV["PDS-PROV<br/>PAOV, PRES, EXEC, COMP, DEBT, REC, TRT"]
        PDS_NAT["PDS-NAT<br/>NAT-PRES, WORKS, TRT"]
    end
    
    subgraph DIA [DIA - Data Integration Adapters]
        SCA_MUNI[SCA-MUNI]
        SCA_PROV[SCA-PROV]
        SCA_NAT[SCA-NAT]
        PPA["PPA<br/>SQL DB + VDB"]
    end
    
    subgraph KAA [KAA - Knowledge AI Agents]
        KBA[KBA - Knowledge Base]
        RAGA[RAGA - RAG Agent]
        TRA[TRA - Trend/Report]
        CRA[CRA - Cross-Reference]
        WOA[WOA - Workflow Orchestrator]
    end
    
    subgraph OEx [OEx - Output Execution]
        ALA[ALA - Alerts]
        RPA_OUT[RPA - Reports]
        APIGW[API-GW]
        WUI[WUI - Web UI]
    end
    
    PDS_MUNI --> SCA_MUNI
    PDS_PROV --> SCA_PROV
    PDS_NAT --> SCA_NAT
    SCA_MUNI --> KBA
    SCA_PROV --> RAGA
    SCA_NAT --> TRA
    PPA -.-> SCA_MUNI & SCA_PROV & SCA_NAT
    KBA --> ALA
    RAGA --> RPA_OUT
    TRA --> APIGW
    CRA --> WUI
    WOA --> KBA & RAGA & TRA & CRA
```

---

## Arquitectura Actual del Repositorio

```mermaid
flowchart TB
    subgraph Extraction [Extraction Layer]
        DL[downloader.py<br/>Boletines CBA only]
        SYNC[sync_service.py]
    end
    
    subgraph Processing [Processing Layer]
        CE[content_extractor.py]
        ME[mencion_extractor.py]
        AP[acto_parser.py]
        BP[batch_processor.py]
    end
    
    subgraph Agents [AI Agents - Minimal]
        DOC_INT[DocumentIntelligence]
        ANOM_DET[AnomalyDetection]
        INS_REP[InsightReporting]
    end
    
    subgraph Storage [Storage]
        SQLITE[(SQLite)]
    end
    
    subgraph Output [Output - Monolithic]
        API[FastAPI REST]
        UI[React Frontend]
    end
    
    DL --> BP
    SYNC --> BP
    BP --> CE --> SQLITE
    CE --> ME & AP
    SQLITE --> Agents
    Agents --> API --> UI
```

---

## Comparativa y Gaps Identificados

| Aspecto | Arquitectura Propuesta | Arquitectura Actual | Gap |

|---------|------------------------|---------------------|-----|

| **Fuentes de datos** | Multi-fuente (MUNI, PROV, NAT) | Single-source (Boletines CBA) | ALTO |

| **Scrapers** | Especializados por portal | Un downloader generico | MEDIO |

| **Adaptadores** | SCA-* por tipo de dato | Sin adaptadores, flujo lineal | ALTO |

| **Vector DB** | VDB para embeddings/RAG | Solo SQLite relacional | ALTO |

| **Agentes IA** | 5+ especializados (KBA, RAGA, TRA, CRA, WOA) | 3 genericos | MEDIO |

| **Orquestacion** | WOA dedicado central | Basica en workflow_crud | MEDIO |

| **Outputs** | Separados (ALA, RPA, API-GW, WUI) | Mezclados en API | BAJO |

---

## Evaluacion del Approach Propuesto

### Fortalezas

1. **Escalabilidad Multi-fuente**: Permite agregar nuevos portales (municipal, nacional) sin modificar el core
2. **Separacion de Concerns**: Cada capa tiene responsabilidad unica
3. **RAG-ready**: Inclusion de VDB habilita busqueda semantica y RAG
4. **Agentes Especializados**: Mejor precision y mantenibilidad

### Consideraciones

1. **Complejidad Inicial**: Requiere mas infraestructura (VDB, mas bases de datos)
2. **Overhead de Coordinacion**: WOA debe manejar comunicacion entre agentes
3. **Datos Disponibles**: Algunos portales (MUNI, NAT) pueden no tener APIs publicas

---

## Plan de Refactorizacion Incremental

### Fase 1: Abstraer Capa de Extraccion (PDS)

Crear interfaz base para scrapers y adaptar el downloader existente:

**Archivos clave:**

- Crear: `watcher-monolith/backend/app/scrapers/base_scraper.py`
- Refactor: [`downloader.py`](watcher-monolith/backend/app/api/v1/endpoints/downloader.py) -> `scrapers/pds_prov.py`
- Crear: `scrapers/pds_muni.py` (placeholder)

### Fase 2: Implementar Capa de Adaptadores (DIA)

Normalizar datos de diferentes fuentes a un schema comun:

**Archivos clave:**

- Crear: `watcher-monolith/backend/app/adapters/base_adapter.py`
- Crear: `adapters/sca_prov.py` (transformar boletines)
- Crear: `adapters/ppa.py` (persistencia unificada)

### Fase 3: Agregar Vector Database

Integrar ChromaDB/Pinecone para embeddings:

**Archivos clave:**

- Modificar: [`database.py`](watcher-monolith/backend/app/db/database.py) - agregar VDB
- Crear: `services/embedding_service.py`
- Modificar: [`batch_processor.py`](watcher-monolith/backend/app/services/batch_processor.py) - generar embeddings

### Fase 4: Especializar Agentes (KAA)

Refactorizar agentes existentes y agregar nuevos:

**Archivos clave:**

- Refactor: [`agents/`](agents/) -> estructura mas modular
- Crear: `agents/kba_agent.py` (Knowledge Base)
- Crear: `agents/raga_agent.py` (RAG con VDB)
- Potenciar: [`agents/document_intelligence.py`](agents/document_intelligence.py)

### Fase 5: Separar Outputs (OEx)

Desacoplar alertas, reportes y API:

**Archivos clave:**

- Crear: `services/alert_dispatcher.py` (ALA)
- Crear: `services/report_generator.py` (RPA)
- Refactor: endpoints para API Gateway pattern

---

## Recomendacion

**El approach es solido y escalable**, pero recomiendo implementarlo **incrementalmente**:

1. **Sprint 3**: Fase 1 - Abstraer scrapers (sin romper funcionalidad actual)
2. **Sprint 4**: Fase 2 + 3 - Adaptadores y Vector DB
3. **Sprint 5**: Fase 4 - Agentes especializados
4. **Sprint 6**: Fase 5 - Separar outputs

Esto permite validar cada capa antes de avanzar y mantener el sistema funcional durante la migracion.