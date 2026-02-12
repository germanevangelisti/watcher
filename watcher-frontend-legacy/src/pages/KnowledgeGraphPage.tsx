import { useState, useEffect, useRef } from 'react';
import {
  Container,
  Title,
  Paper,
  Stack,
  Group,
  Text,
  Badge,
  Card,
  Loader,
  Alert,
  Select,
  NumberInput,
  Button,
  Grid,
  Tabs,
  ScrollArea,
  ActionIcon,
  Tooltip,
  Table,
  Modal
} from '@mantine/core';
import {
  IconGraph,
  IconRefresh,
  IconUser,
  IconBuilding,
  IconBriefcase,
  IconFileText,
  IconCurrencyDollar,
  IconFilter,
  IconTimeline,
  IconAlertTriangle
} from '@tabler/icons-react';
import {
  getKnowledgeGraph,
  getEntidades,
  getEntityHistory,
  detectPatterns
} from '../services/api';
import type { GraphData, EntityNode, PatternDetection, EntityHistoryAnalysis } from '../types/search';

const ENTITY_TYPE_ICONS: Record<string, any> = {
  persona: IconUser,
  organismo: IconBuilding,
  empresa: IconBriefcase,
  contrato: IconFileText,
  monto: IconCurrencyDollar
};

const ENTITY_TYPE_COLORS: Record<string, string> = {
  persona: '#339AF0',
  organismo: '#51CF66',
  empresa: '#FF6B6B',
  contrato: '#FCC419',
  monto: '#9775FA'
};

export default function KnowledgeGraphPage() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [entities, setEntities] = useState<EntityNode[]>([]);
  const [patterns, setPatterns] = useState<PatternDetection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Filtros
  const [maxNodes, setMaxNodes] = useState(50);
  const [minMentions, setMinMentions] = useState(3);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  
  // Canvas ref para dibujar el grafo
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // Modal para detalles de entidad
  const [selectedEntity, setSelectedEntity] = useState<EntityHistoryAnalysis | null>(null);
  const [loadingEntity, setLoadingEntity] = useState(false);

  useEffect(() => {
    loadGraph();
    loadEntities();
    loadPatterns();
  }, []);

  useEffect(() => {
    if (graphData) {
      drawGraph();
    }
  }, [graphData]);

  const loadGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getKnowledgeGraph({
        max_nodes: maxNodes,
        min_mentions: minMentions,
        entity_types: selectedTypes.length > 0 ? selectedTypes : undefined
      });
      setGraphData(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error cargando el grafo');
      console.error('Graph error:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadEntities = async () => {
    try {
      const response = await getEntidades({ limit: 100 });
      setEntities(response.entidades);
    } catch (err) {
      console.error('Error loading entities:', err);
    }
  };

  const loadPatterns = async () => {
    try {
      const data = await detectPatterns({ min_severity: 'medium', limit: 20 });
      setPatterns(data);
    } catch (err) {
      console.error('Error loading patterns:', err);
    }
  };

  const handleEntityClick = async (entityId: string) => {
    setLoadingEntity(true);
    try {
      const history = await getEntityHistory(entityId);
      setSelectedEntity(history);
    } catch (err) {
      console.error('Error loading entity history:', err);
      setError('No se pudo cargar el historial de la entidad');
    } finally {
      setLoadingEntity(false);
    }
  };

  const drawGraph = () => {
    if (!graphData || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Configurar canvas
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    const width = canvas.width;
    const height = canvas.height;

    // Limpiar canvas
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, width, height);

    // Simulación simple de layout (force-directed)
    const nodes = graphData.nodes.map((node, i) => ({
      ...node,
      x: Math.random() * width,
      y: Math.random() * height,
      vx: 0,
      vy: 0
    }));

    const links = graphData.links;

    // Aplicar fuerzas (versión simplificada)
    for (let iteration = 0; iteration < 50; iteration++) {
      // Repulsión entre nodos
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x;
          const dy = nodes[j].y - nodes[i].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 1000 / (dist * dist);
          
          nodes[i].vx -= (dx / dist) * force;
          nodes[i].vy -= (dy / dist) * force;
          nodes[j].vx += (dx / dist) * force;
          nodes[j].vy += (dy / dist) * force;
        }
      }

      // Atracción por enlaces
      links.forEach(link => {
        const source = nodes.find(n => n.id === link.source);
        const target = nodes.find(n => n.id === link.target);
        if (!source || !target) return;

        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - 100) * 0.01;

        source.vx += (dx / dist) * force;
        source.vy += (dy / dist) * force;
        target.vx -= (dx / dist) * force;
        target.vy -= (dy / dist) * force;
      });

      // Aplicar velocidades
      nodes.forEach(node => {
        node.x += node.vx * 0.1;
        node.y += node.vy * 0.1;
        node.vx *= 0.9;
        node.vy *= 0.9;

        // Mantener dentro del canvas
        node.x = Math.max(30, Math.min(width - 30, node.x));
        node.y = Math.max(30, Math.min(height - 30, node.y));
      });
    }

    // Dibujar enlaces
    ctx.strokeStyle = '#adb5bd';
    ctx.lineWidth = 1;
    links.forEach(link => {
      const source = nodes.find(n => n.id === link.source);
      const target = nodes.find(n => n.id === link.target);
      if (!source || !target) return;

      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      ctx.globalAlpha = link.confidence * 0.5 + 0.2;
      ctx.stroke();
      ctx.globalAlpha = 1;
    });

    // Dibujar nodos
    nodes.forEach(node => {
      const color = ENTITY_TYPE_COLORS[node.type] || '#868e96';
      const radius = Math.min(30, 10 + Math.log(node.mentions + 1) * 3);

      // Círculo
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Etiqueta
      ctx.fillStyle = '#000';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(
        node.label.length > 20 ? node.label.substring(0, 17) + '...' : node.label,
        node.x,
        node.y + radius + 12
      );
    });
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'red';
      case 'high': return 'orange';
      case 'medium': return 'yellow';
      default: return 'gray';
    }
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between">
          <div>
            <Title order={2}>🕸️ Grafo de Conocimiento</Title>
            <Text c="dimmed" size="sm">
              Visualización de entidades y sus relaciones extraídas de los boletines
            </Text>
          </div>
          <Button
            leftSection={<IconRefresh size={16} />}
            onClick={loadGraph}
            loading={loading}
          >
            Actualizar
          </Button>
        </Group>

        {/* Filtros */}
        <Paper p="md" withBorder>
          <Group>
            <NumberInput
              label="Máximo de nodos"
              value={maxNodes}
              onChange={(val) => setMaxNodes(typeof val === 'number' ? val : 50)}
              min={10}
              max={200}
              step={10}
              style={{ width: 150 }}
            />
            <NumberInput
              label="Mínimo menciones"
              value={minMentions}
              onChange={(val) => setMinMentions(typeof val === 'number' ? val : 3)}
              min={1}
              max={20}
              style={{ width: 150 }}
            />
            <Button onClick={loadGraph} leftSection={<IconFilter size={16} />}>
              Aplicar Filtros
            </Button>
          </Group>
        </Paper>

        {/* Error */}
        {error && (
          <Alert color="red" title="Error" onClose={() => setError(null)} withCloseButton>
            {error}
          </Alert>
        )}

        <Tabs defaultValue="graph">
          <Tabs.List>
            <Tabs.Tab value="graph" leftSection={<IconGraph size={16} />}>
              Visualización
            </Tabs.Tab>
            <Tabs.Tab value="entities" leftSection={<IconUser size={16} />}>
              Entidades ({entities.length})
            </Tabs.Tab>
            <Tabs.Tab value="patterns" leftSection={<IconAlertTriangle size={16} />}>
              Patrones Sospechosos ({patterns.length})
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="graph" pt="md">
            {loading ? (
              <Paper p="xl" withBorder>
                <Group justify="center">
                  <Loader />
                  <Text>Cargando grafo...</Text>
                </Group>
              </Paper>
            ) : graphData ? (
              <Paper withBorder p={0}>
                <canvas
                  ref={canvasRef}
                  style={{
                    width: '100%',
                    height: '600px',
                    cursor: 'pointer'
                  }}
                />
                <Paper p="md" bg="gray.0">
                  <Grid>
                    <Grid.Col span={4}>
                      <Text size="sm" fw={600}>Nodos: {graphData.nodes.length}</Text>
                    </Grid.Col>
                    <Grid.Col span={4}>
                      <Text size="sm" fw={600}>Enlaces: {graphData.links.length}</Text>
                    </Grid.Col>
                    <Grid.Col span={4}>
                      <Group gap="xs">
                        {Object.entries(ENTITY_TYPE_COLORS).map(([type, color]) => (
                          <Badge key={type} color={color} variant="filled" size="xs">
                            {type}
                          </Badge>
                        ))}
                      </Group>
                    </Grid.Col>
                  </Grid>
                </Paper>
              </Paper>
            ) : (
              <Paper p="xl" withBorder>
                <Text c="dimmed" ta="center">
                  No hay datos del grafo disponibles
                </Text>
              </Paper>
            )}
          </Tabs.Panel>

          <Tabs.Panel value="entities" pt="md">
            <Paper withBorder>
              <ScrollArea h={600}>
                <Table highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Tipo</Table.Th>
                      <Table.Th>Nombre</Table.Th>
                      <Table.Th>Menciones</Table.Th>
                      <Table.Th>Primera Aparición</Table.Th>
                      <Table.Th>Última Aparición</Table.Th>
                      <Table.Th>Acciones</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {entities.map((entity) => {
                      const Icon = ENTITY_TYPE_ICONS[entity.tipo];
                      return (
                        <Table.Tr key={entity.id}>
                          <Table.Td>
                            <Badge
                              leftSection={Icon && <Icon size={14} />}
                              color={ENTITY_TYPE_COLORS[entity.tipo]}
                              variant="light"
                            >
                              {entity.tipo}
                            </Badge>
                          </Table.Td>
                          <Table.Td>
                            <Text fw={500}>{entity.nombre}</Text>
                          </Table.Td>
                          <Table.Td>
                            <Badge variant="light">{entity.total_menciones}</Badge>
                          </Table.Td>
                          <Table.Td>
                            <Text size="sm" c="dimmed">{entity.primera_aparicion}</Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="sm" c="dimmed">{entity.ultima_aparicion}</Text>
                          </Table.Td>
                          <Table.Td>
                            <Tooltip label="Ver historial">
                              <ActionIcon
                                variant="light"
                                onClick={() => handleEntityClick(entity.id)}
                              >
                                <IconTimeline size={16} />
                              </ActionIcon>
                            </Tooltip>
                          </Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              </ScrollArea>
            </Paper>
          </Tabs.Panel>

          <Tabs.Panel value="patterns" pt="md">
            <Stack gap="md">
              {patterns.map((pattern, idx) => (
                <Card key={idx} padding="lg" withBorder>
                  <Group justify="space-between" mb="sm">
                    <Group>
                      <IconAlertTriangle color={getSeverityColor(pattern.severity)} />
                      <Text fw={600}>{pattern.pattern_name}</Text>
                    </Group>
                    <Badge color={getSeverityColor(pattern.severity)} variant="filled">
                      {pattern.severity}
                    </Badge>
                  </Group>
                  <Text size="sm" c="dimmed" mb="md">
                    {pattern.description}
                  </Text>
                  <Group gap="xs" mb="sm">
                    {pattern.entities.slice(0, 5).map((entity, i) => (
                      <Badge key={i} variant="light">
                        {entity}
                      </Badge>
                    ))}
                    {pattern.entities.length > 5 && (
                      <Badge variant="outline">
                        +{pattern.entities.length - 5} más
                      </Badge>
                    )}
                  </Group>
                  <Text size="xs" c="dimmed">
                    {pattern.estadisticas.total_casos} casos detectados
                    {' • '}
                    {pattern.estadisticas.periodo_inicio} - {pattern.estadisticas.periodo_fin}
                  </Text>
                </Card>
              ))}
              {patterns.length === 0 && (
                <Paper p="xl" withBorder>
                  <Text c="dimmed" ta="center">
                    No se detectaron patrones sospechosos
                  </Text>
                </Paper>
              )}
            </Stack>
          </Tabs.Panel>
        </Tabs>
      </Stack>

      {/* Modal para historial de entidad */}
      <Modal
        opened={selectedEntity !== null}
        onClose={() => setSelectedEntity(null)}
        size="xl"
        title={`Historial: ${selectedEntity?.entidad.nombre}`}
      >
        {loadingEntity ? (
          <Group justify="center" p="xl">
            <Loader />
          </Group>
        ) : selectedEntity && (
          <Stack gap="md">
            <Group>
              <Badge color={ENTITY_TYPE_COLORS[selectedEntity.entidad.tipo]}>
                {selectedEntity.entidad.tipo}
              </Badge>
              <Badge variant="light">
                {selectedEntity.estadisticas.total_documentos} documentos
              </Badge>
              <Badge variant="light">
                {selectedEntity.estadisticas.total_relaciones} relaciones
              </Badge>
            </Group>
            
            <Text size="sm">
              <strong>Periodo de actividad:</strong>{' '}
              {selectedEntity.estadisticas.periodo_actividad.inicio} -{' '}
              {selectedEntity.estadisticas.periodo_actividad.fin}
            </Text>

            {selectedEntity.patrones_sospechosos.length > 0 && (
              <Alert color="orange" title="Patrones Sospechosos">
                {selectedEntity.patrones_sospechosos.map((p, i) => (
                  <Text key={i} size="sm">• {p.pattern_name}</Text>
                ))}
              </Alert>
            )}

            <ScrollArea h={300}>
              <Stack gap="xs">
                {selectedEntity.timeline.eventos.map((evento, i) => (
                  <Paper key={i} p="xs" withBorder>
                    <Group justify="space-between">
                      <Text size="sm">{evento.fecha}</Text>
                      <Text size="xs" c="dimmed">{evento.boletin_filename}</Text>
                    </Group>
                    <Text size="xs" lineClamp={2}>{evento.contexto}</Text>
                  </Paper>
                ))}
              </Stack>
            </ScrollArea>
          </Stack>
        )}
      </Modal>
    </Container>
  );
}
