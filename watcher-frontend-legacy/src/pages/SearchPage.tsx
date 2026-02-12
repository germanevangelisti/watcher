import { useState } from 'react';
import {
  Container,
  Title,
  Paper,
  TextInput,
  Button,
  Stack,
  Group,
  Text,
  Badge,
  Card,
  Loader,
  Alert,
  ActionIcon,
  Tooltip,
  Select,
  NumberInput,
  Collapse,
  ScrollArea,
  SegmentedControl,
  Divider,
  Progress,
  Center
} from '@mantine/core';
import {
  IconSearch,
  IconFilter,
  IconExternalLink,
  IconFileText,
  IconCalendar,
  IconMapPin,
  IconAdjustments,
  IconDownload,
  IconCheck,
  IconAlertCircle,
  IconArrowUp,
  IconArrowDown
} from '@tabler/icons-react';
import { searchEmbeddings, getDocumentText } from '../services/api';
import type { SearchResult, SearchRequest } from '../types/search';
import { DocumentModal } from '../components/shared/DocumentModal';

type SortBy = 'relevance' | 'date' | 'filename';
type SearchModel = 'default' | 'multilingual' | 'fast';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  
  // Filtros
  const [yearFilter, setYearFilter] = useState<string | null>(null);
  const [monthFilter, setMonthFilter] = useState<string | null>(null);
  const [sectionFilter, setSectionFilter] = useState<string | null>(null);
  const [nResults, setNResults] = useState<number>(10);
  
  // Ordenamiento y modelo
  const [sortBy, setSortBy] = useState<SortBy>('relevance');
  const [searchModel, setSearchModel] = useState<SearchModel>('default');
  
  // Modal para ver documento completo
  const [selectedDoc, setSelectedDoc] = useState<{ filename: string; content: string } | null>(null);
  const [loadingDoc, setLoadingDoc] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) {
      setError('Por favor ingresa un término de búsqueda');
      return;
    }

    setLoading(true);
    setError(null);
    setResults([]);

    try {
      const request: SearchRequest = {
        query: query.trim(),
        n_results: nResults,
        filters: {},
        model: searchModel  // Enviar modelo seleccionado
      };

      if (yearFilter) request.filters!.year = yearFilter;
      if (monthFilter) request.filters!.month = monthFilter;
      if (sectionFilter) request.filters!.section = sectionFilter;

      const response = await searchEmbeddings(request);
      
      // Aplicar ordenamiento
      let sortedResults = [...response.results];
      if (sortBy === 'date') {
        sortedResults.sort((a, b) => b.metadata.date.localeCompare(a.metadata.date));
      } else if (sortBy === 'filename') {
        sortedResults.sort((a, b) => a.metadata.filename.localeCompare(b.metadata.filename));
      }
      // 'relevance' ya viene ordenado por score del backend
      
      setResults(sortedResults);
      setExecutionTime(response.execution_time_ms);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error al realizar la búsqueda');
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDocument = async (filename: string) => {
    setLoadingDoc(true);
    setError(null);
    try {
      const doc = await getDocumentText(filename);
      setSelectedDoc(doc);
    } catch (err: any) {
      console.error('Error loading document:', err);
      const errorMsg = err.response?.data?.detail || 'No se pudo cargar el documento completo';
      setError(errorMsg);
    } finally {
      setLoadingDoc(false);
    }
  };

  const highlightText = (text: string, query: string) => {
    if (!query.trim()) return text;
    
    const terms = query.toLowerCase().split(' ').filter(t => t.length > 2);
    let highlighted = text;
    
    terms.forEach(term => {
      const regex = new RegExp(`(${term})`, 'gi');
      highlighted = highlighted.replace(regex, '<mark>$1</mark>');
    });
    
    return highlighted;
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.7) return 'green';
    if (score >= 0.5) return 'blue';
    if (score >= 0.3) return 'yellow';
    return 'gray';
  };

  const downloadDocument = async (filename: string) => {
    try {
      const response = await fetch(`http://localhost:8001/api/v1/documentos/text/${filename}/download`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename.replace('.pdf', '.txt');
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError('Error al descargar el documento');
    }
  };

  const getModelDescription = (model: SearchModel) => {
    switch (model) {
      case 'default':
        return 'Modelo estándar (equilibrado)';
      case 'multilingual':
        return 'Modelo multilingüe (mejor para español)';
      case 'fast':
        return 'Modelo rápido (menor latencia)';
    }
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        {/* Header */}
        <div>
          <Group justify="space-between" mb="md">
            <div>
              <Title order={2}>🔍 Búsqueda Semántica</Title>
              <Text c="dimmed" size="sm" mt={4}>
                Busca contenido en los boletines oficiales usando búsqueda semántica inteligente
              </Text>
            </div>
            <Button
              variant="light"
              leftSection={<IconAdjustments size={16} />}
              onClick={() => setShowFilters(!showFilters)}
            >
              {showFilters ? 'Ocultar Opciones' : 'Mostrar Opciones'}
            </Button>
          </Group>
        </div>

        {/* Opciones avanzadas */}
        <Collapse in={showFilters}>
          <Paper p="md" withBorder>
            <Stack gap="md">
              {/* Modelo de búsqueda */}
              <div>
                <Text size="sm" fw={600} mb="xs">
                  Modelo de Búsqueda
                </Text>
                <SegmentedControl
                  fullWidth
                  value={searchModel}
                  onChange={(value) => setSearchModel(value as SearchModel)}
                  data={[
                    { label: '⚡ Estándar', value: 'default' },
                    { label: '🌐 Multilingüe', value: 'multilingual' },
                    { label: '🚀 Rápido', value: 'fast' }
                  ]}
                />
                <Text size="xs" c="dimmed" mt={4}>
                  {getModelDescription(searchModel)}
                </Text>
              </div>

              <Divider />

              {/* Filtros */}
              <div>
                <Text size="sm" fw={600} mb="xs">
                  Filtros de Búsqueda
                </Text>
                <Group grow>
                  <Select
                    label="Año"
                    placeholder="Todos"
                    clearable
                    value={yearFilter}
                    onChange={setYearFilter}
                    data={['2024', '2025', '2026']}
                  />
                  <Select
                    label="Mes"
                    placeholder="Todos"
                    clearable
                    value={monthFilter}
                    onChange={setMonthFilter}
                    data={[
                      { value: '01', label: 'Enero' },
                      { value: '02', label: 'Febrero' },
                      { value: '03', label: 'Marzo' },
                      { value: '04', label: 'Abril' },
                      { value: '05', label: 'Mayo' },
                      { value: '06', label: 'Junio' },
                      { value: '07', label: 'Julio' },
                      { value: '08', label: 'Agosto' },
                      { value: '09', label: 'Septiembre' },
                      { value: '10', label: 'Octubre' },
                      { value: '11', label: 'Noviembre' },
                      { value: '12', label: 'Diciembre' }
                    ]}
                  />
                  <Select
                    label="Sección"
                    placeholder="Todas"
                    clearable
                    value={sectionFilter}
                    onChange={setSectionFilter}
                    data={[
                      { value: '1', label: 'Sección 1' },
                      { value: '2', label: 'Sección 2' },
                      { value: '3', label: 'Sección 3' },
                      { value: '4', label: 'Sección 4' },
                      { value: '5', label: 'Sección 5' }
                    ]}
                  />
                  <NumberInput
                    label="Resultados"
                    placeholder="10"
                    value={nResults}
                    onChange={(val) => setNResults(typeof val === 'number' ? val : 10)}
                    min={5}
                    max={50}
                    step={5}
                  />
                </Group>
              </div>
            </Stack>
          </Paper>
        </Collapse>

        {/* Barra de búsqueda */}
        <Paper p="md" withBorder>
          <Group align="flex-end">
            <TextInput
              style={{ flex: 1 }}
              placeholder="Ej: contratos de construcción de obras públicas..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              size="lg"
              leftSection={<IconSearch size={20} />}
            />
            <Button
              size="lg"
              onClick={handleSearch}
              loading={loading}
              leftSection={<IconSearch size={18} />}
            >
              Buscar
            </Button>
          </Group>
        </Paper>

        {/* Error */}
        {error && (
          <Alert color="red" title="Error" onClose={() => setError(null)} withCloseButton>
            {error}
          </Alert>
        )}

        {/* Loading */}
        {loading && (
          <Paper p="xl" withBorder>
            <Group justify="center">
              <Loader size="lg" />
              <Text>Buscando en documentos indexados...</Text>
            </Group>
          </Paper>
        )}

        {/* Resultados */}
        {!loading && results.length > 0 && (
          <>
            {/* Header de resultados con ordenamiento */}
            <Paper p="md" withBorder>
              <Group justify="space-between">
                <div>
                  <Text fw={600}>
                    {results.length} resultados encontrados
                    {executionTime && <Text span c="dimmed" fw={400}> en {executionTime.toFixed(0)}ms</Text>}
                  </Text>
                  <Progress
                    value={100}
                    size="xs"
                    mt={8}
                    color="blue"
                    animated
                  />
                </div>
                <Group gap="xs">
                  <Text size="sm" c="dimmed">Ordenar por:</Text>
                  <SegmentedControl
                    size="xs"
                    value={sortBy}
                    onChange={(value) => {
                      setSortBy(value as SortBy);
                      // Re-aplicar ordenamiento
                      let sorted = [...results];
                      if (value === 'date') {
                        sorted.sort((a, b) => b.metadata.date.localeCompare(a.metadata.date));
                      } else if (value === 'filename') {
                        sorted.sort((a, b) => a.metadata.filename.localeCompare(b.metadata.filename));
                      } else {
                        sorted.sort((a, b) => b.score - a.score);
                      }
                      setResults(sorted);
                    }}
                    data={[
                      { label: '⭐ Relevancia', value: 'relevance' },
                      { label: '📅 Fecha', value: 'date' },
                      { label: '📄 Nombre', value: 'filename' }
                    ]}
                  />
                </Group>
              </Group>
            </Paper>

            <Stack gap="md">
              {results.map((result, idx) => (
                <Card key={idx} padding="lg" withBorder shadow="sm">
                  <Stack gap="sm">
                    {/* Header del resultado */}
                    <Group justify="space-between">
                      <Group gap="xs">
                        <IconFileText size={20} />
                        <Text fw={600} size="lg">{result.metadata.filename}</Text>
                        <Badge
                          size="lg"
                          color={getScoreColor(result.score)}
                          variant="light"
                          leftSection={
                            result.score >= 0.7 ? <IconCheck size={14} /> : 
                            result.score >= 0.5 ? <IconArrowUp size={14} /> :
                            <IconArrowDown size={14} />
                          }
                        >
                          {(result.score * 100).toFixed(1)}% relevancia
                        </Badge>
                      </Group>
                      <Group gap="xs">
                        <Tooltip label="Ver documento completo">
                          <ActionIcon
                            variant="light"
                            size="lg"
                            color="blue"
                            onClick={() => handleViewDocument(result.metadata.filename)}
                            loading={loadingDoc}
                          >
                            <IconExternalLink size={18} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Descargar documento">
                          <ActionIcon
                            variant="light"
                            size="lg"
                            color="green"
                            onClick={() => downloadDocument(result.metadata.filename)}
                          >
                            <IconDownload size={18} />
                          </ActionIcon>
                        </Tooltip>
                      </Group>
                    </Group>

                    {/* Metadata mejorada */}
                    <Group gap="lg">
                      <Group gap="xs">
                        <IconCalendar size={16} color="gray" />
                        <Text size="sm" c="dimmed">
                          {result.metadata.date}
                        </Text>
                      </Group>
                      <Group gap="xs">
                        <IconMapPin size={16} color="gray" />
                        <Text size="sm" c="dimmed">
                          {result.metadata.section}
                        </Text>
                      </Group>
                      <Badge variant="dot" size="sm">
                        Chunk {result.metadata.chunk_id?.split('_').pop() || 'N/A'}
                      </Badge>
                    </Group>

                    {/* Contenido del fragmento con mejor diseño */}
                    <Paper p="md" bg="gray.0" withBorder radius="md">
                      <ScrollArea h={120}>
                        <Text
                          size="sm"
                          style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}
                          dangerouslySetInnerHTML={{
                            __html: highlightText(result.document, query)
                          }}
                        />
                      </ScrollArea>
                    </Paper>
                  </Stack>
                </Card>
              ))}
            </Stack>
          </>
        )}

        {/* Sin resultados */}
        {!loading && results.length === 0 && query && (
          <Paper p="xl" withBorder>
            <Stack align="center" gap="md">
              <IconSearch size={48} opacity={0.3} />
              <Text c="dimmed">No se encontraron resultados para tu búsqueda</Text>
              <Text size="sm" c="dimmed">
                Intenta con otros términos o ajusta los filtros
              </Text>
            </Stack>
          </Paper>
        )}
      </Stack>

      {/* Modal para documento completo */}
      <DocumentModal
        isOpen={selectedDoc !== null}
        onClose={() => setSelectedDoc(null)}
        filename={selectedDoc?.filename || null}
        content={selectedDoc?.content || null}
        isLoading={loadingDoc}
        onDownload={() => selectedDoc && downloadDocument(selectedDoc.filename)}
      />
    </Container>
  );
}
