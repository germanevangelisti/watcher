import { useState } from 'react';
import {
  Modal,
  Stack,
  Text,
  Button,
  Group,
  Stepper,
  Alert,
  Code,
  Progress,
  Badge,
  Title,
  Paper,
  ThemeIcon,
  Grid,
} from '@mantine/core';
import {
  IconCheck,
  IconFileText,
  IconDatabase,
  IconAlertCircle,
  IconPlayerPlay,
} from '@tabler/icons-react';
import {
  extractDocumentText,
  indexDocumentEmbeddings,
  getDocumentProcessingStatus,
} from '../../services/api';

interface DocumentProcessingModalProps {
  opened: boolean;
  onClose: () => void;
  documentId: number;
  documentName: string;
  onComplete: () => void;
}

export function DocumentProcessingModal({
  opened,
  onClose,
  documentId,
  documentName,
  onComplete,
}: DocumentProcessingModalProps) {
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [extractionResult, setExtractionResult] = useState<any>(null);
  const [embeddingsResult, setEmbeddingsResult] = useState<any>(null);

  // Debug detallado
  console.log('🟣 DocumentProcessingModal RENDER:', {
    opened,
    documentId,
    documentName,
    timestamp: new Date().toISOString()
  });

  const handleExtractText = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await extractDocumentText(documentId);
      setExtractionResult(result.extraction);
      setActive(1);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Error al extraer texto');
    } finally {
      setLoading(false);
    }
  };

  const handleIndexEmbeddings = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('🔵 Iniciando indexación de embeddings para doc:', documentId);
      
      const result = await indexDocumentEmbeddings(documentId);
      
      console.log('✅ Embeddings generados:', result);
      
      setEmbeddingsResult(result.embeddings);
      setActive(2);
    } catch (err: any) {
      console.error('❌ Error en indexación:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Error al indexar embeddings';
      console.error('Error completo:', errorMsg);
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (active === 2) {
      onComplete();
    }
    setActive(0);
    setExtractionResult(null);
    setEmbeddingsResult(null);
    setError(null);
    onClose();
  };

  console.log('🟢 Modal render state:', { opened, documentId, documentName });

  // Si el documentId es 0 o inválido, no renderizar
  if (!documentId || documentId === 0) {
    console.warn('⚠️ Modal con documentId inválido:', documentId);
    return null;
  }

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span>Procesar: {documentName}</span>
          <Badge color="blue" variant="light">ID: {documentId}</Badge>
        </div>
      }
      size="xl"
      centered
      closeOnClickOutside={false}
      closeOnEscape={false}
      withCloseButton={true}
      trapFocus={true}
      overlayProps={{ 
        opacity: 0.85, 
        blur: 6,
        backgroundOpacity: 0.85
      }}
      styles={{
        inner: { 
          padding: '0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0
        },
        content: { 
          maxWidth: '900px',
          width: '90vw',
          maxHeight: '90vh',
          overflow: 'auto',
          position: 'relative',
          backgroundColor: 'white'
        },
        header: { 
          padding: '1.5rem',
          borderBottom: '1px solid #e9ecef',
          backgroundColor: '#f8f9fa'
        },
        body: { 
          padding: '1.5rem',
          backgroundColor: 'white'
        },
        overlay: {
          backgroundColor: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(6px)'
        }
      }}
      zIndex={999999}
      portalProps={{ target: document.body }}
    >
      <Stack gap="md">
        {/* Banner de debug visible */}
        <Alert color="blue" icon={<IconAlertCircle size="1rem" />} variant="filled">
          <Text size="sm" fw={600}>
            Modal cargado correctamente - Doc ID: {documentId}
          </Text>
        </Alert>

        <Text size="sm" c="dimmed">
          Pipeline de procesamiento: extrae texto del PDF → genera embeddings → indexa para búsqueda RAG
        </Text>

        <Stepper active={active} breakpoint="sm">
          <Stepper.Step
            label="Extracción"
            description="Extraer texto del PDF"
            icon={<IconFileText size="1.2rem" />}
            loading={loading && active === 0}
            completedIcon={<IconCheck size="1.2rem" />}
          >
            <Stack gap="md" mt="md">
              {!extractionResult ? (
                <>
                  <Text size="sm">
                    Este paso extrae el texto completo del PDF y lo prepara para procesamiento.
                  </Text>
                  <Button
                    onClick={handleExtractText}
                    loading={loading}
                    leftSection={<IconPlayerPlay size="1rem" />}
                  >
                    Extraer Texto
                  </Button>
                </>
              ) : (
                <Paper p="md" withBorder>
                  <Stack gap="xs">
                    <Group justify="space-between">
                      <Text fw={600}>Resultado de Extracción</Text>
                      <Badge color="green" variant="light">
                        Completado
                      </Badge>
                    </Group>

                    <Group gap="lg">
                      <div>
                        <Text size="xs" c="dimmed">
                          Páginas
                        </Text>
                        <Text size="lg" fw={700}>
                          {extractionResult.num_pages}
                        </Text>
                      </div>
                      <div>
                        <Text size="xs" c="dimmed">
                          Caracteres
                        </Text>
                        <Text size="lg" fw={700}>
                          {extractionResult.total_chars.toLocaleString()}
                        </Text>
                      </div>
                      <div>
                        <Text size="xs" c="dimmed">
                          Tokens
                        </Text>
                        <Text size="lg" fw={700}>
                          {extractionResult.total_tokens.toLocaleString()}
                        </Text>
                      </div>
                    </Group>

                    <div>
                      <Text size="sm" fw={500} mb={5}>
                        Preview del texto extraído:
                      </Text>
                      <Code block style={{ maxHeight: 200, overflow: 'auto' }}>
                        {extractionResult.preview}
                      </Code>
                    </div>

                    <Button onClick={() => setActive(1)} mt="md">
                      Continuar al Siguiente Paso
                    </Button>
                  </Stack>
                </Paper>
              )}
            </Stack>
          </Stepper.Step>

          <Stepper.Step
            label="Indexación"
            description="Generar embeddings"
            icon={<IconDatabase size="1.2rem" />}
            loading={loading && active === 1}
            completedIcon={<IconCheck size="1.2rem" />}
          >
            <Stack gap="md" mt="md">
              {!embeddingsResult ? (
                <>
                  <Text size="sm">
                    Este paso genera embeddings (vectores) del texto usando Google Gemini para habilitar búsqueda semántica RAG.
                  </Text>
                  
                  <Alert color="blue" icon={<IconAlertCircle size="1rem" />}>
                    <Stack gap="xs">
                      <Text size="xs" fw={600}>
                        Proceso de Indexación:
                      </Text>
                      <ul style={{ margin: '5px 0', paddingLeft: '20px', fontSize: '12px' }}>
                        <li>División del documento en chunks (~1000 tokens)</li>
                        <li>Generación de embeddings con Google AI</li>
                        <li>Indexación en ChromaDB para búsqueda RAG</li>
                      </ul>
                      <Text size="xs" c="dimmed">
                        ⏱️ Este proceso puede tomar 30-60 segundos dependiendo del tamaño.
                      </Text>
                    </Stack>
                  </Alert>

                  {loading && (
                    <Paper p="md" withBorder bg="blue.0">
                      <Stack gap="xs">
                        <Group>
                          <Progress value={100} animated style={{ flex: 1 }} />
                        </Group>
                        <Text size="sm" fw={600} c="blue">
                          🔄 Procesando documento...
                        </Text>
                        <Text size="xs" c="dimmed">
                          Generando embeddings con Google Gemini. Por favor espera...
                        </Text>
                        {/* Logs en tiempo real para el usuario */}
                        <div style={{ 
                          fontFamily: 'monospace', 
                          fontSize: '11px', 
                          backgroundColor: '#1a1b1e',
                          color: '#00ff00',
                          padding: '10px',
                          borderRadius: '4px',
                          maxHeight: '150px',
                          overflow: 'auto'
                        }}>
                          <div>→ Extrayendo texto del PDF...</div>
                          <div>→ Dividiendo en chunks...</div>
                          <div>→ Conectando con Google AI API...</div>
                          <div>→ Generando vectores de embeddings...</div>
                          <div>→ Indexando en ChromaDB...</div>
                          <div style={{ color: '#ffff00' }}>⏳ Esto puede tomar un momento...</div>
                        </div>
                      </Stack>
                    </Paper>
                  )}

                  <Button
                    onClick={handleIndexEmbeddings}
                    loading={loading}
                    leftSection={<IconPlayerPlay size="1rem" />}
                    disabled={!extractionResult || loading}
                    size="md"
                    fullWidth
                  >
                    {loading ? 'Generando Embeddings...' : 'Generar Embeddings'}
                  </Button>
                </>
              ) : (
                <Paper p="md" withBorder>
                  <Stack gap="xs">
                    <Group justify="space-between">
                      <Text fw={600}>Embeddings Generados</Text>
                      <Badge color="green" variant="light">
                        Indexado
                      </Badge>
                    </Group>

                    <Group gap="lg">
                      <div>
                        <Text size="xs" c="dimmed">
                          Modelo
                        </Text>
                        <Text size="sm" fw={600}>
                          {embeddingsResult.model}
                        </Text>
                      </div>
                      <div>
                        <Text size="xs" c="dimmed">
                          Chunks
                        </Text>
                        <Text size="lg" fw={700}>
                          {embeddingsResult.num_chunks}
                        </Text>
                      </div>
                      <div>
                        <Text size="xs" c="dimmed">
                          Tokens Totales
                        </Text>
                        <Text size="lg" fw={700}>
                          {embeddingsResult.total_tokens.toLocaleString()}
                        </Text>
                      </div>
                    </Group>

                    <Alert color="green" icon={<IconCheck size="1rem" />} mt="md">
                      ¡Documento procesado e indexado correctamente! Ahora está disponible para búsqueda semántica
                      RAG.
                    </Alert>

                    <Button onClick={() => setActive(2)} mt="md">
                      Ver Resumen
                    </Button>
                  </Stack>
                </Paper>
              )}
            </Stack>
          </Stepper.Step>

          <Stepper.Completed>
            <Stack gap="lg" mt="md" align="center">
              <ThemeIcon size={80} radius="xl" variant="light" color="green">
                <IconCheck size={48} />
              </ThemeIcon>
              
              <div style={{ textAlign: 'center' }}>
                <Title order={2} mb="xs">¡Procesamiento Completado!</Title>
                <Text c="dimmed" size="lg">
                  El documento ha sido procesado completamente y está listo para búsqueda semántica.
                </Text>
              </div>

              {extractionResult && embeddingsResult && (
                <Paper p="xl" withBorder w="100%" shadow="sm">
                  <Stack gap="md">
                    <Group justify="space-between">
                      <Text fw={700} size="lg">Resumen del Procesamiento</Text>
                      <Badge size="lg" color="green" variant="light">
                        Completado
                      </Badge>
                    </Group>

                    <Grid gutter="lg">
                      <Grid.Col span={4}>
                        <Paper p="md" withBorder bg="gray.0">
                          <Stack gap={5} align="center">
                            <ThemeIcon size="lg" variant="light" color="blue">
                              <IconFileText size="1.5rem" />
                            </ThemeIcon>
                            <Text size="xs" c="dimmed" fw={500} tt="uppercase">
                              Páginas
                            </Text>
                            <Text size="xl" fw={700}>
                              {extractionResult.num_pages}
                            </Text>
                          </Stack>
                        </Paper>
                      </Grid.Col>

                      <Grid.Col span={4}>
                        <Paper p="md" withBorder bg="gray.0">
                          <Stack gap={5} align="center">
                            <ThemeIcon size="lg" variant="light" color="violet">
                              <IconDatabase size="1.5rem" />
                            </ThemeIcon>
                            <Text size="xs" c="dimmed" fw={500} tt="uppercase">
                              Chunks
                            </Text>
                            <Text size="xl" fw={700}>
                              {embeddingsResult.num_chunks}
                            </Text>
                          </Stack>
                        </Paper>
                      </Grid.Col>

                      <Grid.Col span={4}>
                        <Paper p="md" withBorder bg="gray.0">
                          <Stack gap={5} align="center">
                            <ThemeIcon size="lg" variant="light" color="green">
                              <IconCheck size="1.5rem" />
                            </ThemeIcon>
                            <Text size="xs" c="dimmed" fw={500} tt="uppercase">
                              Tokens
                            </Text>
                            <Text size="xl" fw={700}>
                              {embeddingsResult.total_tokens.toLocaleString()}
                            </Text>
                          </Stack>
                        </Paper>
                      </Grid.Col>
                    </Grid>

                    <Alert color="green" icon={<IconCheck size="1rem" />} variant="light">
                      <Text size="sm" fw={500}>
                        El documento <strong>{documentName}</strong> está ahora indexado y disponible para:
                      </Text>
                      <ul style={{ marginTop: '0.5rem', marginBottom: 0 }}>
                        <li>Búsqueda semántica en el sistema RAG</li>
                        <li>Análisis de compliance automático</li>
                        <li>Consultas de chat sobre su contenido</li>
                      </ul>
                    </Alert>
                  </Stack>
                </Paper>
              )}

              <Button onClick={handleClose} fullWidth size="lg" mt="md" color="green">
                Cerrar y Ver Documento Actualizado
              </Button>
            </Stack>
          </Stepper.Completed>
        </Stepper>

        {error && (
          <Alert icon={<IconAlertCircle size="1rem" />} title="Error" color="red" mt="md">
            {error}
          </Alert>
        )}

        {loading && (
          <div>
            <Text size="sm" mb={5}>
              Procesando...
            </Text>
            <Progress value={100} animated />
          </div>
        )}
      </Stack>
    </Modal>
  );
}
