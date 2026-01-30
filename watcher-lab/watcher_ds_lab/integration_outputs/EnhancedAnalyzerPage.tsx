
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
