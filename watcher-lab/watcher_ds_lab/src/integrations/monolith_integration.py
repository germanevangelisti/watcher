"""
🔗 INTEGRACIÓN CON WATCHER MONOLITH
Conecta el agente DS Lab con el sistema monolítico existente
"""

import json
import logging
import requests
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sys

# Imports locales
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import BASE_DIR
from agents.detection_agent import WatcherDetectionAgent, RedFlag

logger = logging.getLogger(__name__)

@dataclass
class MonolithConfig:
    """Configuración para la integración con el monolito"""
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    pdf_base_path: str = "/Users/germanevangelisti/watcher-agent/watcher-monolith/backend/data/raw"
    processed_base_path: str = "/Users/germanevangelisti/watcher-agent/watcher-monolith/backend/data/processed"
    
class MonolithIntegration:
    """
    Clase principal para integrar DS Lab con Watcher Monolith
    """
    
    def __init__(self, config: Optional[MonolithConfig] = None):
        self.config = config or MonolithConfig()
        self.agent = WatcherDetectionAgent()
        
        logger.info("MonolithIntegration inicializada")
        logger.info(f"Backend URL: {self.config.backend_url}")
        logger.info(f"PDF Path: {self.config.pdf_base_path}")
    
    def create_enhanced_batch_endpoint(self) -> str:
        """
        Genera el código para un nuevo endpoint en el monolito que incluya análisis DS Lab
        """
        
        endpoint_code = '''
# Agregar al archivo: /watcher-monolith/backend/app/api/v1/endpoints/watcher.py

from pathlib import Path
import sys
import json
from typing import Dict, List, Optional

# Importar agente DS Lab
ds_lab_path = "/Users/germanevangelisti/watcher-agent/watcher-lab/watcher_ds_lab/src"
sys.path.append(ds_lab_path)

from agents.detection_agent import WatcherDetectionAgent
from integrations.pdf_evidence_viewer import PDFEvidenceViewer

@router.post("/analyze-with-redflags", response_model=Dict)
async def analyze_document_with_redflags(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Análisis completo del documento con detección de red flags
    """
    try:
        # Procesar documento (código existente del monolito)
        result = await process_single_document(file)
        
        # Agregar análisis DS Lab
        agent = WatcherDetectionAgent()
        pdf_viewer = PDFEvidenceViewer()
        
        # Convertir resultado a formato compatible
        document_data = {
            'filename': file.filename,
            'transparency_score': result.get('transparency_score', 50),
            'risk_level': result.get('risk_level', 'MEDIO'),
            'num_amounts': len(result.get('amounts', [])),
            'num_entities': len(result.get('entities', [])),
            'seccion': result.get('section', 1),
            'act_type': result.get('act_type', 'OTROS')
        }
        
        # Detectar red flags
        red_flags = agent.analyze_document(document_data)
        
        # Agregar evidencia visual para cada red flag
        enhanced_flags = []
        for flag in red_flags:
            evidence_data = pdf_viewer.extract_evidence_coordinates(
                file_path=Path(file.filename),
                red_flag=flag
            )
            
            flag_dict = asdict(flag)
            flag_dict['visual_evidence'] = evidence_data
            enhanced_flags.append(flag_dict)
        
        # Resultado enriquecido
        enhanced_result = {
            **result,
            'red_flags': enhanced_flags,
            'red_flags_count': len(red_flags),
            'critical_flags': len([f for f in red_flags if f.severity == 'CRITICO']),
            'ds_lab_analysis': True
        }
        
        return enhanced_result
        
    except Exception as e:
        logger.error(f"Error en análisis con red flags: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/redflags/{document_id}")
async def get_document_redflags(document_id: str):
    """
    Obtiene red flags específicas de un documento
    """
    try:
        # Buscar documento en base de datos del monolito
        document = get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        # Analizar con DS Lab
        agent = WatcherDetectionAgent()
        red_flags = agent.analyze_document(document)
        
        return {
            'document_id': document_id,
            'red_flags': [asdict(flag) for flag in red_flags],
            'summary': {
                'total': len(red_flags),
                'critical': len([f for f in red_flags if f.severity == 'CRITICO']),
                'high': len([f for f in red_flags if f.severity == 'ALTO'])
            }
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo red flags: {e}")
        raise HTTPException(status_code=500, detail=str(e))
'''
        
        return endpoint_code
    
    def create_frontend_redflags_component(self) -> str:
        """
        Genera componente React para visualizar red flags
        """
        
        component_code = '''
// Archivo: /watcher-monolith/frontend/src/components/RedFlagsViewer.tsx

import React, { useState, useEffect } from 'react';
import {
  Card,
  Badge,
  Group,
  Text,
  Stack,
  Alert,
  Button,
  Modal,
  List,
  Timeline,
  Highlight,
  ActionIcon,
  Tooltip
} from '@mantine/core';
import {
  IconAlertTriangle,
  IconEye,
  IconDownload,
  IconFlag,
  IconExclamationMark
} from '@tabler/icons-react';

interface RedFlag {
  id: string;
  flag_type: string;
  severity: 'CRITICO' | 'ALTO' | 'MEDIO' | 'INFORMATIVO';
  confidence: number;
  description: string;
  evidence: string[];
  recommendation: string;
  visual_evidence?: {
    page: number;
    coordinates: { x: number; y: number; width: number; height: number }[];
    highlighted_text: string[];
  };
}

interface RedFlagsViewerProps {
  documentId: string;
  redFlags: RedFlag[];
  pdfUrl?: string;
}

const RedFlagsViewer: React.FC<RedFlagsViewerProps> = ({ 
  documentId, 
  redFlags, 
  pdfUrl 
}) => {
  const [selectedFlag, setSelectedFlag] = useState<RedFlag | null>(null);
  const [modalOpened, setModalOpened] = useState(false);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICO': return 'red';
      case 'ALTO': return 'orange';
      case 'MEDIO': return 'yellow';
      case 'INFORMATIVO': return 'blue';
      default: return 'gray';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'CRITICO': return <IconExclamationMark size={16} />;
      case 'ALTO': return <IconAlertTriangle size={16} />;
      default: return <IconFlag size={16} />;
    }
  };

  const handleViewEvidence = (flag: RedFlag) => {
    setSelectedFlag(flag);
    setModalOpened(true);
  };

  const handleViewInPDF = (flag: RedFlag) => {
    if (pdfUrl && flag.visual_evidence) {
      const params = new URLSearchParams({
        page: flag.visual_evidence.page.toString(),
        highlight: JSON.stringify(flag.visual_evidence.coordinates)
      });
      window.open(`${pdfUrl}?${params}`, '_blank');
    }
  };

  return (
    <>
      <Card withBorder shadow="sm" radius="md">
        <Group justify="space-between" mb="md">
          <Text size="lg" fw={500}>Red Flags Detectadas</Text>
          <Badge size="lg" variant="light" color={redFlags.length > 0 ? 'red' : 'green'}>
            {redFlags.length} detectadas
          </Badge>
        </Group>

        {redFlags.length === 0 ? (
          <Alert icon={<IconFlag size={16} />} title="Sin red flags" color="green">
            No se detectaron irregularidades en este documento.
          </Alert>
        ) : (
          <Stack gap="sm">
            {redFlags.map((flag, index) => (
              <Card key={flag.id} withBorder radius="sm" p="sm">
                <Group justify="space-between" align="flex-start">
                  <Stack gap="xs" style={{ flex: 1 }}>
                    <Group gap="xs">
                      <Badge 
                        color={getSeverityColor(flag.severity)}
                        variant="filled"
                        leftSection={getSeverityIcon(flag.severity)}
                      >
                        {flag.severity}
                      </Badge>
                      <Text size="sm" c="dimmed">
                        Confianza: {(flag.confidence * 100).toFixed(1)}%
                      </Text>
                    </Group>
                    
                    <Text fw={500} size="sm">
                      {flag.flag_type.replace(/_/g, ' ')}
                    </Text>
                    
                    <Text size="sm" c="dimmed">
                      {flag.description}
                    </Text>
                    
                    <Group gap="xs">
                      <Button 
                        size="xs" 
                        variant="light"
                        leftSection={<IconEye size={14} />}
                        onClick={() => handleViewEvidence(flag)}
                      >
                        Ver Evidencia
                      </Button>
                      
                      {flag.visual_evidence && pdfUrl && (
                        <Tooltip label="Ver en PDF original">
                          <ActionIcon 
                            variant="light" 
                            color="blue"
                            onClick={() => handleViewInPDF(flag)}
                          >
                            <IconDownload size={14} />
                          </ActionIcon>
                        </Tooltip>
                      )}
                    </Group>
                  </Stack>
                </Group>
              </Card>
            ))}
          </Stack>
        )}
      </Card>

      {/* Modal de evidencia detallada */}
      <Modal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        title={`Evidencia: ${selectedFlag?.flag_type.replace(/_/g, ' ')}`}
        size="lg"
      >
        {selectedFlag && (
          <Stack gap="md">
            <Alert 
              icon={getSeverityIcon(selectedFlag.severity)}
              color={getSeverityColor(selectedFlag.severity)}
              title={`Severidad: ${selectedFlag.severity}`}
            >
              {selectedFlag.description}
            </Alert>

            <div>
              <Text size="sm" fw={500} mb="xs">Evidencia encontrada:</Text>
              <List size="sm">
                {selectedFlag.evidence.map((evidence, idx) => (
                  <List.Item key={idx}>{evidence}</List.Item>
                ))}
              </List>
            </div>

            <div>
              <Text size="sm" fw={500} mb="xs">Recomendación:</Text>
              <Text size="sm" c="dimmed">
                {selectedFlag.recommendation}
              </Text>
            </div>

            {selectedFlag.visual_evidence && (
              <div>
                <Text size="sm" fw={500} mb="xs">Ubicación en documento:</Text>
                <Text size="sm" c="dimmed">
                  Página {selectedFlag.visual_evidence.page}
                </Text>
                
                {selectedFlag.visual_evidence.highlighted_text.length > 0 && (
                  <div>
                    <Text size="sm" fw={500} mt="xs" mb="xs">Texto destacado:</Text>
                    {selectedFlag.visual_evidence.highlighted_text.map((text, idx) => (
                      <Highlight 
                        key={idx}
                        highlight={text}
                        highlightStyles={{ backgroundColor: 'yellow', color: 'black' }}
                      >
                        {text}
                      </Highlight>
                    ))}
                  </div>
                )}

                <Button 
                  mt="md"
                  variant="filled"
                  leftSection={<IconEye size={16} />}
                  onClick={() => handleViewInPDF(selectedFlag)}
                  fullWidth
                >
                  Abrir PDF en ubicación exacta
                </Button>
              </div>
            )}
          </Stack>
        )}
      </Modal>
    </>
  );
};

export default RedFlagsViewer;
'''
        
        return component_code
    
    def create_enhanced_analyzer_page(self) -> str:
        """
        Genera código para mejorar la página del analizador con red flags
        """
        
        enhanced_page = '''
// Modificar: /watcher-monolith/frontend/src/pages/AnalyzerPage.tsx

import React, { useState } from 'react';
import { Container, Title, Space, Grid, Card, Text, Button, Group } from '@mantine/core';
import { IconUpload, IconAnalyze, IconFlag } from '@tabler/icons-react';
import RedFlagsViewer from '../components/RedFlagsViewer';

const AnalyzerPage: React.FC = () => {
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [redFlags, setRedFlags] = useState([]);

  const handleAnalyze = async (file: File) => {
    setIsAnalyzing(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      // Usar el nuevo endpoint con red flags
      const response = await fetch('/api/v1/analyze-with-redflags', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      setAnalysisResult(result);
      setRedFlags(result.red_flags || []);
      
    } catch (error) {
      console.error('Error en análisis:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <Container size="xl">
      <Title order={1} mb="lg">Analizador de Documentos con Red Flags</Title>
      
      <Grid>
        <Grid.Col span={6}>
          <Card withBorder shadow="sm" radius="md" p="lg">
            <Group justify="space-between" mb="md">
              <Text size="lg" fw={500}>Subir Documento</Text>
              <IconUpload size={24} />
            </Group>
            
            {/* Componente de upload existente */}
            
            {analysisResult && (
              <div>
                <Text size="lg" fw={500} mt="xl" mb="md">Resultado del Análisis</Text>
                
                <Text size="sm" mb="xs">
                  Score de Transparencia: {analysisResult.transparency_score}/100
                </Text>
                
                <Text size="sm" mb="xs">
                  Nivel de Riesgo: {analysisResult.risk_level}
                </Text>
                
                <Text size="sm" mb="xs">
                  Red Flags Detectadas: {analysisResult.red_flags_count}
                </Text>
                
                {analysisResult.critical_flags > 0 && (
                  <Text size="sm" color="red" fw={500}>
                    ⚠️ {analysisResult.critical_flags} red flags críticas requieren atención inmediata
                  </Text>
                )}
              </div>
            )}
          </Card>
        </Grid.Col>
        
        <Grid.Col span={6}>
          {redFlags.length > 0 && (
            <RedFlagsViewer
              documentId={analysisResult?.document_id || 'current'}
              redFlags={redFlags}
              pdfUrl={`/api/v1/documents/${analysisResult?.document_id}/pdf`}
            />
          )}
        </Grid.Col>
      </Grid>
    </Container>
  );
};

export default AnalyzerPage;
'''
        
        return enhanced_page
    
    def sync_datasets_with_monolith(self) -> Dict[str, any]:
        """
        Sincroniza datasets del DS Lab con la base de datos del monolito
        """
        try:
            # Cargar datos del DS Lab
            data_files = list(Path("data/raw").glob("dataset_boletines_cordoba_agosto2025_*.csv"))
            if not data_files:
                return {"error": "No se encontró dataset del DS Lab"}
            
            df = pd.read_csv(data_files[0])
            
            # Analizar todos los documentos para obtener red flags
            report = self.agent.analyze_dataset(df)
            
            # Estructura para sincronización
            sync_data = {
                "total_documents": len(df),
                "documents_with_flags": len([doc for doc in report['top_problematic_documents']]),
                "critical_documents": [
                    doc['document'] for doc in report['top_problematic_documents'] 
                    if 'CRITICO' in doc['severities']
                ],
                "sync_timestamp": pd.Timestamp.now().isoformat(),
                "red_flags_by_document": {}
            }
            
            # Procesar cada documento
            for _, row in df.iterrows():
                doc_id = row['filename']
                red_flags = self.agent.analyze_document(row.to_dict())
                
                sync_data['red_flags_by_document'][doc_id] = {
                    "red_flags_count": len(red_flags),
                    "critical_count": len([f for f in red_flags if f.severity == 'CRITICO']),
                    "high_count": len([f for f in red_flags if f.severity == 'ALTO']),
                    "flags": [asdict(flag) for flag in red_flags]
                }
            
            # Guardar datos de sincronización
            sync_file = BASE_DIR / "reports" / "monolith_sync.json"
            with open(sync_file, 'w', encoding='utf-8') as f:
                json.dump(sync_data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Sincronización completada: {sync_file}")
            
            return sync_data
            
        except Exception as e:
            logger.error(f"Error en sincronización: {e}")
            return {"error": str(e)}
    
    def create_migration_script(self) -> str:
        """
        Crea script SQL para agregar red flags a la base de datos del monolito
        """
        
        migration_sql = '''
-- Migración para agregar red flags a Watcher Monolith
-- Ejecutar en: /watcher-monolith/backend/sqlite.db

-- Tabla para almacenar red flags
CREATE TABLE IF NOT EXISTS red_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flag_id VARCHAR(255) UNIQUE NOT NULL,
    document_id VARCHAR(255) NOT NULL,
    flag_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('CRITICO', 'ALTO', 'MEDIO', 'INFORMATIVO')),
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    description TEXT NOT NULL,
    evidence TEXT, -- JSON array
    recommendation TEXT,
    transparency_score REAL,
    risk_factors TEXT, -- JSON object
    metadata TEXT, -- JSON object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para optimización
CREATE INDEX IF NOT EXISTS idx_red_flags_document_id ON red_flags(document_id);
CREATE INDEX IF NOT EXISTS idx_red_flags_severity ON red_flags(severity);
CREATE INDEX IF NOT EXISTS idx_red_flags_flag_type ON red_flags(flag_type);
CREATE INDEX IF NOT EXISTS idx_red_flags_created_at ON red_flags(created_at);

-- Tabla para coordenadas visuales en PDFs
CREATE TABLE IF NOT EXISTS pdf_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    red_flag_id INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    coordinates TEXT NOT NULL, -- JSON con x, y, width, height
    highlighted_text TEXT,
    context_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (red_flag_id) REFERENCES red_flags(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pdf_evidence_red_flag_id ON pdf_evidence(red_flag_id);
CREATE INDEX IF NOT EXISTS idx_pdf_evidence_page ON pdf_evidence(page_number);

-- Vista para consultas optimizadas
CREATE VIEW IF NOT EXISTS red_flags_summary AS
SELECT 
    document_id,
    COUNT(*) as total_flags,
    SUM(CASE WHEN severity = 'CRITICO' THEN 1 ELSE 0 END) as critical_flags,
    SUM(CASE WHEN severity = 'ALTO' THEN 1 ELSE 0 END) as high_flags,
    SUM(CASE WHEN severity = 'MEDIO' THEN 1 ELSE 0 END) as medium_flags,
    SUM(CASE WHEN severity = 'INFORMATIVO' THEN 1 ELSE 0 END) as info_flags,
    AVG(confidence) as avg_confidence,
    MIN(transparency_score) as min_transparency,
    MAX(created_at) as last_analysis
FROM red_flags 
GROUP BY document_id;

-- Trigger para actualizar updated_at
CREATE TRIGGER IF NOT EXISTS update_red_flags_timestamp 
    AFTER UPDATE ON red_flags
BEGIN
    UPDATE red_flags SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
'''
        
        return migration_sql
    
    def generate_integration_guide(self) -> str:
        """
        Genera guía completa de integración
        """
        
        guide = f'''
# 🔗 GUÍA DE INTEGRACIÓN WATCHER DS LAB ↔ MONOLITH

## 📋 PASOS DE INTEGRACIÓN

### 1. BACKEND (FastAPI)

**a) Agregar endpoints de red flags:**
```bash
# Ubicación: /watcher-monolith/backend/app/api/v1/endpoints/watcher.py
# Agregar el código generado por create_enhanced_batch_endpoint()
```

**b) Configurar base de datos:**
```bash
cd /watcher-monolith/backend
sqlite3 sqlite.db < migration.sql
```

**c) Instalar dependencias adicionales:**
```bash
pip install pandas numpy scikit-learn
```

### 2. FRONTEND (React)

**a) Agregar componente RedFlagsViewer:**
```bash
# Crear archivo: /watcher-monolith/frontend/src/components/RedFlagsViewer.tsx
# Usar código generado por create_frontend_redflags_component()
```

**b) Actualizar AnalyzerPage:**
```bash
# Modificar: /watcher-monolith/frontend/src/pages/AnalyzerPage.tsx
# Usar código generado por create_enhanced_analyzer_page()
```

**c) Instalar dependencias:**
```bash
cd /watcher-monolith/frontend
npm install @tabler/icons-react
```

### 3. INTEGRACIÓN DE DATOS

**a) Sincronizar datasets:**
```python
from integrations.monolith_integration import MonolithIntegration

integration = MonolithIntegration()
sync_result = integration.sync_datasets_with_monolith()
```

**b) Configurar rutas de archivos:**
```python
# Actualizar paths en config/settings.py:
MONOLITH_PDF_PATH = "{self.config.pdf_base_path}"
MONOLITH_PROCESSED_PATH = "{self.config.processed_base_path}"
```

## 🎯 FUNCIONALIDADES INTEGRADAS

### Red Flags en Tiempo Real
- ✅ Detección automática durante análisis
- ✅ Clasificación por severidad (CRÍTICO, ALTO, MEDIO, INFORMATIVO)
- ✅ Evidencia visual en PDFs
- ✅ Recomendaciones específicas

### Visualización Avanzada
- ✅ Componente React para mostrar red flags
- ✅ Modal con evidencia detallada
- ✅ Botón para abrir PDF en ubicación exacta
- ✅ Badges de severidad con iconos

### Persistencia de Datos
- ✅ Tabla red_flags en SQLite
- ✅ Coordenadas visuales en pdf_evidence
- ✅ Vistas optimizadas para consultas
- ✅ Índices para rendimiento

## 🚀 COMANDOS DE DESPLIEGUE

### Desarrollo
```bash
# Backend
cd /watcher-monolith/backend
uvicorn app.main:app --reload

# Frontend  
cd /watcher-monolith/frontend
npm run dev
```

### Producción
```bash
# Build frontend
cd /watcher-monolith/frontend
npm run build

# Deploy backend
cd /watcher-monolith/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📊 FLUJO DE USO

1. **Usuario sube PDF** en frontend
2. **Backend procesa** con análisis existente + DS Lab
3. **Red flags detectadas** automáticamente
4. **Resultado muestra** análisis tradicional + red flags
5. **Usuario puede ver** evidencia específica en PDF
6. **Click en "Ver en PDF"** abre documento en ubicación exacta

## 🎯 BENEFICIOS DE LA INTEGRACIÓN

### Para Auditores:
- ✅ **Priorización automática** de documentos críticos
- ✅ **Evidencia visual** directa en PDFs
- ✅ **Recomendaciones específicas** para cada irregularidad

### Para Desarrolladores:
- ✅ **API unificada** con capacidades ML
- ✅ **Componentes reutilizables** React
- ✅ **Base de datos estructurada** para red flags

### Para Ciudadanos:
- ✅ **Transparencia mejorada** con alertas automáticas
- ✅ **Acceso directo** a evidencia en documentos
- ✅ **Interfaz intuitiva** para consultar irregularidades

## 🔍 PRÓXIMOS PASOS

1. **Implementar autenticación** para red flags sensibles
2. **Dashboard ejecutivo** con métricas de red flags
3. **Alertas por email** para casos críticos
4. **API pública** para desarrolladores cívicos
5. **Integración con sistemas** gubernamentales oficiales

---

*Integración completada entre Watcher DS Lab v2.0 y Watcher Monolith* ✅
'''
        
        return guide

def main():
    """
    Script principal para generar la integración
    """
    print("🔗 Generando integración Watcher DS Lab ↔ Monolith...")
    
    integration = MonolithIntegration()
    
    # Crear directorio de outputs
    output_dir = Path("integration_outputs")
    output_dir.mkdir(exist_ok=True)
    
    # Generar archivos de integración
    files_generated = []
    
    # 1. Endpoint backend
    endpoint_code = integration.create_enhanced_batch_endpoint()
    endpoint_file = output_dir / "enhanced_watcher_endpoints.py"
    with open(endpoint_file, 'w', encoding='utf-8') as f:
        f.write(endpoint_code)
    files_generated.append(str(endpoint_file))
    
    # 2. Componente frontend
    component_code = integration.create_frontend_redflags_component()
    component_file = output_dir / "RedFlagsViewer.tsx"
    with open(component_file, 'w', encoding='utf-8') as f:
        f.write(component_code)
    files_generated.append(str(component_file))
    
    # 3. Página mejorada
    page_code = integration.create_enhanced_analyzer_page()
    page_file = output_dir / "EnhancedAnalyzerPage.tsx"
    with open(page_file, 'w', encoding='utf-8') as f:
        f.write(page_code)
    files_generated.append(str(page_file))
    
    # 4. Migración SQL
    migration_sql = integration.create_migration_script()
    migration_file = output_dir / "migration_redflags.sql"
    with open(migration_file, 'w', encoding='utf-8') as f:
        f.write(migration_sql)
    files_generated.append(str(migration_file))
    
    # 5. Guía de integración
    guide = integration.generate_integration_guide()
    guide_file = output_dir / "INTEGRATION_GUIDE.md"
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(guide)
    files_generated.append(str(guide_file))
    
    # 6. Sincronizar datos
    sync_result = integration.sync_datasets_with_monolith()
    
    print("\n✅ Integración generada exitosamente!")
    print(f"\n📁 Archivos generados:")
    for file in files_generated:
        print(f"  • {file}")
    
    print(f"\n📊 Sincronización de datos:")
    print(f"  • Documentos: {sync_result.get('total_documents', 0)}")
    print(f"  • Con red flags: {sync_result.get('documents_with_flags', 0)}")
    print(f"  • Críticos: {len(sync_result.get('critical_documents', []))}")
    
    return files_generated

if __name__ == "__main__":
    main()
