import { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Group,
  Text,
  Badge,
  ActionIcon,
  Stack,
  Alert,
  Loader,
  Pagination,
  Tooltip,
  Paper
} from '@mantine/core';
import {
  IconFileText,
  IconAnalyze,
  IconAlertCircle,
  IconCheck,
  IconClock,
  IconX,
  IconEye
} from '@tabler/icons-react';
import { processBoletin } from '../../services/api';
import { JurisdiccionSelector, JurisdiccionBadge } from '../../components/jurisdicciones/JurisdiccionSelector';

const API_BASE_URL = 'http://localhost:8001';

interface BoletinDocument {
  id: number;
  filename: string;
  year: number;
  month: number;
  day: number;
  section: number;
  file_size_bytes: number;
  analysis_status: string;
  last_analyzed: string | null;
  created_at: string;
  jurisdiccion_nombre?: string;
  jurisdiccion_tipo?: string;
}

export function BoletinesTab() {
  const [documents, setDocuments] = useState<BoletinDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [processingDoc, setProcessingDoc] = useState<number | null>(null);
  const [selectedJurisdiccion, setSelectedJurisdiccion] = useState<number | null>(null);
  const pageSize = 50;

  useEffect(() => {
    loadDocuments();
  }, [page, selectedJurisdiccion]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError('');
      
      const skip = (page - 1) * pageSize;
      
      // Usar el endpoint real de boletines
      const params = new URLSearchParams({
        skip: skip.toString(),
        limit: pageSize.toString()
      });
      
      if (selectedJurisdiccion) {
        params.append('jurisdiccion_id', selectedJurisdiccion.toString());
      }
      
      const response = await fetch(
        `${API_BASE_URL}/api/v1/boletines?${params.toString()}`
      );
      
      if (!response.ok) {
        throw new Error('Error al cargar documentos');
      }
      
      const boletines = await response.json();
      
      // Transformar boletines al formato esperado por la UI
      const transformedDocs = Array.isArray(boletines) ? boletines.map((b: any) => {
        // Extraer año, mes, día del campo date (YYYYMMDD)
        const dateStr = b.date || '00000000';
        const year = parseInt(dateStr.substring(0, 4)) || 0;
        const month = parseInt(dateStr.substring(4, 6)) || 0;
        const day = parseInt(dateStr.substring(6, 8)) || 0;
        
        return {
          id: b.id,
          filename: b.filename,
          year,
          month,
          day,
          section: parseInt(b.section) || 0,
          file_size_bytes: 0, // No tenemos este dato, usar 0
          analysis_status: b.status || 'pending',
          last_analyzed: b.updated_at,
          created_at: b.created_at,
          jurisdiccion_nombre: b.jurisdiccion_nombre,
          jurisdiccion_tipo: b.jurisdiccion_tipo
        };
      }) : [];
      
      setDocuments(transformedDocs);
      
      // Obtener estadísticas para paginación
      const statsResponse = await fetch(`${API_BASE_URL}/api/v1/boletines/stats-wizard`);
      if (statsResponse.ok) {
        const stats = await statsResponse.json();
        const total = stats.total_bulletins || transformedDocs.length;
        setTotalDocuments(total);
        setTotalPages(Math.max(1, Math.ceil(total / pageSize)));
      } else {
        setTotalDocuments(transformedDocs.length);
        setTotalPages(1);
      }
    } catch (err) {
      setError('Error cargando documentos: ' + (err as Error).message);
      console.error('Error details:', err);
      setDocuments([]); // Asegurar que documents es un array vacío en caso de error
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <IconCheck size={18} color="green" />;
      case 'processing':
        return <IconClock size={18} color="blue" />;
      case 'failed':
        return <IconX size={18} color="red" />;
      default:
        return <IconAlertCircle size={18} color="gray" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      completed: 'green',
      processing: 'blue',
      failed: 'red',
      pending: 'gray',
    };
    return <Badge color={colors[status] || 'gray'}>{status}</Badge>;
  };

  const formatDate = (doc: BoletinDocument) => {
    return `${doc.day}/${doc.month}/${doc.year}`;
  };

  const formatSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const getSectionName = (section: number) => {
    const sections: Record<number, string> = {
      1: 'Compras y Contrataciones',
      2: 'Obras Públicas',
      3: 'Subsidios y Transferencias',
      4: 'Designaciones y Decretos',
      5: 'Notificaciones Judiciales'
    };
    return sections[section] || `Sección ${section}`;
  };

  const handleViewDocument = (doc: BoletinDocument) => {
    window.open(
      `${API_BASE_URL}/api/v1/boletines/documents/${doc.filename}/pdf`,
      '_blank',
      'noopener,noreferrer'
    );
  };

  const handleAnalyzeDocument = async (doc: BoletinDocument) => {
    try {
      setProcessingDoc(doc.id);
      await processBoletin(doc.filename);
      await loadDocuments();
    } catch (err) {
      setError(`Error analizando ${doc.filename}: ${(err as Error).message}`);
      console.error(err);
    } finally {
      setProcessingDoc(null);
    }
  };

  if (loading && documents.length === 0) {
    return (
      <Stack align="center" py="xl">
        <Loader size="lg" />
        <Text>Cargando boletines...</Text>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      {error && (
        <Alert icon={<IconAlertCircle size={16} />} color="red" title="Error">
          {error}
        </Alert>
      )}

      {/* Filtros */}
      <Paper p="md" withBorder>
        <Group>
          <div style={{ flex: 1, minWidth: '300px' }}>
            <Text size="sm" fw={500} mb="xs">Filtrar por Jurisdicción</Text>
            <JurisdiccionSelector
              value={selectedJurisdiccion}
              onChange={setSelectedJurisdiccion}
              showStats={true}
              placeholder="Todas las jurisdicciones"
            />
          </div>
        </Group>
      </Paper>

      <Group justify="space-between">
        <Text size="sm" c="dimmed">
          {documents.length > 0
            ? `Mostrando ${documents.length} de ${totalDocuments || '...'} documentos`
            : 'No hay documentos'}
        </Text>
        <Group>
          <Button
            onClick={loadDocuments}
            variant="light"
            loading={loading}
            leftSection={<IconFileText size={16} />}
          >
            Actualizar
          </Button>
        </Group>
      </Group>

      <Table striped highlightOnHover>
        <thead>
          <tr>
            <th>Estado</th>
            <th>Archivo</th>
            <th>Fecha</th>
            <th>Sección</th>
            <th>Tamaño</th>
            <th>Última Análisis</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {documents && documents.length > 0 ? (
            documents.map((doc) => (
              <tr key={doc.id}>
                <td>
                  <Group gap="xs">
                    {getStatusIcon(doc.analysis_status)}
                    {getStatusBadge(doc.analysis_status)}
                  </Group>
                </td>
                <td>
                  <Text size="sm" fw={500}>{doc.filename}</Text>
                  {doc.jurisdiccion_nombre && (
                    <Text size="xs" c="dimmed">{doc.jurisdiccion_nombre}</Text>
                  )}
                </td>
                <td>
                  <Text size="sm">{formatDate(doc)}</Text>
                </td>
                <td>
                  <Badge variant="light" size="sm">{getSectionName(doc.section)}</Badge>
                </td>
                <td>
                  <Text size="xs" c="dimmed">
                    {doc.file_size_bytes > 0 ? formatSize(doc.file_size_bytes) : 'N/A'}
                  </Text>
                </td>
                <td>
                  <Text size="xs" c="dimmed">
                    {doc.last_analyzed ? new Date(doc.last_analyzed).toLocaleDateString('es-AR') : 'Nunca'}
                  </Text>
                </td>
                <td>
                  <Group gap={4}>
                    <Tooltip label="Ver documento">
                      <ActionIcon
                        color="blue"
                        variant="light"
                        size="sm"
                        onClick={() => handleViewDocument(doc)}
                      >
                        <IconEye size={14} />
                      </ActionIcon>
                    </Tooltip>
                    <Tooltip label="Analizar con Agentes IA">
                      <ActionIcon
                        color="green"
                      variant="light"
                      size="sm"
                      disabled={doc.analysis_status === 'processing' || processingDoc === doc.id}
                      loading={processingDoc === doc.id}
                      onClick={() => handleAnalyzeDocument(doc)}
                    >
                      <IconAnalyze size={14} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </td>
            </tr>
          ))
          ) : (
            <tr>
              <td colSpan={7}>
                <Stack align="center" py="xl">
                  <IconFileText size={48} style={{ opacity: 0.3 }} />
                  <Text c="dimmed">No hay boletines para mostrar</Text>
                  <Text size="sm" c="dimmed">Los documentos se cargarán automáticamente cuando estén disponibles</Text>
                </Stack>
              </td>
            </tr>
          )}
        </tbody>
      </Table>

      {/* Pagination */}
      {totalPages > 1 && (
        <Group justify="center" mt="md">
          <Pagination
            total={totalPages}
            value={page}
            onChange={setPage}
            size="sm"
          />
        </Group>
      )}
    </Stack>
  );
}
