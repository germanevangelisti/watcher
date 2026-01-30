import { useState } from 'react';
import { 
  Paper, 
  Button, 
  Stack, 
  Group,
  Text,
  Select,
  Title,
  Badge,
  TextInput,
  NumberInput
} from '@mantine/core';
import { 
  IconPlayerPlay, 
  IconFileAnalytics,
  IconSearch,
  IconCalendar,
  IconTrendingUp
} from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

interface WorkflowActionsProps {
  onWorkflowStarted?: () => void;
}

export function WorkflowActions({ onWorkflowStarted }: WorkflowActionsProps) {
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [workflowType, setWorkflowType] = useState<string>('');
  
  // Custom period form state
  const [startYear, setStartYear] = useState(2025);
  const [startMonth, setStartMonth] = useState(1);
  const [endYear, setEndYear] = useState(2025);
  const [endMonth, setEndMonth] = useState(11);
  const [analysisType, setAnalysisType] = useState<string>('trend_analysis');


  const startWorkflow = async (type: string, params: any = {}) => {
    setLoading(true);
    try {
      // Mapear tipo de workflow a agente responsable
      const agentMap: Record<string, string> = {
        'analyze_high_risk': 'anomaly_detection',
        'monthly_summary': 'insight_reporting',
        'trend_analysis': 'insight_reporting',
        'entity_search': 'document_intelligence'
      };

      const agent = agentMap[type] || 'insight_reporting';

      // Crear request con el formato esperado por el backend
      const workflowRequest = {
        workflow_name: `${type}_${Date.now()}`,
        tasks: [
          {
            task_type: type,
            agent: agent,
            parameters: params,
            priority: 0,
            requires_approval: false
          }
        ],
        config: {}
      };

      const response = await fetch('http://localhost:8001/api/v1/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflowRequest)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('Workflow creation error:', errorData);
        throw new Error(errorData.detail || 'Failed to start workflow');
      }

      const data = await response.json();
      
      // Ejecutar el workflow después de crearlo
      const executeResponse = await fetch(`http://localhost:8001/api/v1/workflows/${data.workflow_id}/execute`, {
        method: 'POST'
      });

      if (!executeResponse.ok) {
        throw new Error('Failed to execute workflow');
      }

      notifications.show({
        title: '🚀 Workflow Iniciado',
        message: `Workflow "${type}" iniciado exitosamente (ID: ${data.workflow_id})`,
        color: 'green'
      });

      setModalOpen(false);
      onWorkflowStarted?.();
      
    } catch (error) {
      console.error('Error starting workflow:', error);
      notifications.show({
        title: '❌ Error',
        message: error instanceof Error ? error.message : 'No se pudo iniciar el workflow',
        color: 'red'
      });
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    {
      id: 'analyze_high_risk',
      title: 'Analizar Alto Riesgo',
      description: 'Analiza documentos con bajo score de transparencia',
      icon: <IconFileAnalytics size={20} />,
      color: 'red',
      action: () => startWorkflow('analyze_high_risk', { threshold: 50, limit: 20 })
    },
    {
      id: 'monthly_summary',
      title: 'Resumen Mensual',
      description: 'Genera resumen de Agosto 2025',
      icon: <IconCalendar size={20} />,
      color: 'blue',
      action: () => startWorkflow('monthly_summary', { year: 2025, month: 8 })
    },
    {
      id: 'trend_analysis',
      title: 'Análisis de Tendencias',
      description: 'Evolución Ene-Nov 2025 (11 meses)',
      icon: <IconTrendingUp size={20} />,
      color: 'green',
      action: () => startWorkflow('trend_analysis', { start_year: 2025, start_month: 1, end_year: 2025, end_month: 11 })
    },
    {
      id: 'custom_period',
      title: 'Análisis Personalizado',
      description: 'Configura período y parámetros específicos',
      icon: <IconCalendar size={20} />,
      color: 'cyan',
      action: () => {
        setWorkflowType('custom_period');
        setModalOpen(true);
      }
    },
    {
      id: 'entity_search',
      title: 'Búsqueda de Entidades',
      description: 'Busca beneficiarios o entidades específicas',
      icon: <IconSearch size={20} />,
      color: 'violet',
      action: () => {
        setWorkflowType('entity_search');
        setModalOpen(true);
      }
    }
  ];

  return (
    <>
      <Paper p="md" withBorder>
        <Group mb="md">
          <IconPlayerPlay size={20} />
          <Title order={4}>⚡ Acciones Rápidas</Title>
        </Group>
        
        <Paper p="sm" mb="md" style={{ backgroundColor: 'var(--mantine-color-blue-0)', border: '1px solid var(--mantine-color-blue-3)' }}>
          <Text size="sm" fw={500} mb="xs">¿Cómo funcionan las Acciones Rápidas?</Text>
          <Text size="xs" c="dimmed" mb="xs">
            Las acciones rápidas inician <strong>workflows de agentes inteligentes</strong> que analizan automáticamente tus documentos.
            Cada workflow ejecuta tareas específicas usando IA y te muestra resultados en tiempo real.
          </Text>
          <Text size="xs" c="dimmed" mb="xs">
            📅 <strong>Análisis por Período:</strong> Puedes analizar datos de meses específicos o rangos temporales completos.
            Los agentes calcularán estadísticas, detectarán tendencias y generarán informes personalizados.
          </Text>
          <Text size="xs" c="dimmed">
            💡 <strong>Tip:</strong> Los workflows se ejecutan en segundo plano. Monitorea su progreso en tiempo real más abajo.
          </Text>
        </Paper>
        
        <Text size="sm" c="dimmed" mb="md">
          🎯 Inicia workflows de análisis sobre tus 1,063 documentos oficiales
        </Text>

        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
          {quickActions.map((action) => (
            <Paper 
              key={action.id} 
              p="md" 
              withBorder 
              style={{ 
                cursor: 'pointer',
                transition: 'transform 0.2s, box-shadow 0.2s',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                }
              }}
              onClick={action.action}
            >
              <Group mb="xs">
                <Badge color={action.color} variant="light" leftSection={action.icon}>
                  {action.title}
                </Badge>
              </Group>
              <Text size="sm" c="dimmed">
                {action.description}
              </Text>
            </Paper>
          ))}
        </SimpleGrid>
      </Paper>

      {/* Custom Modal - Reemplazando Modal de Mantine que no funciona */}
      {modalOpen && (
        <>
          {/* Overlay */}
          <div 
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              zIndex: 9998,
              backdropFilter: 'blur(3px)'
            }}
            onClick={() => {
              setModalOpen(false);
              setWorkflowType('');
            }}
          />
          
          {/* Modal Content */}
          <div
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              backgroundColor: 'white',
              borderRadius: '8px',
              boxShadow: '0 10px 40px rgba(0,0,0,0.3)',
              zIndex: 9999,
              width: workflowType === 'custom_period' ? '90%' : '500px',
              maxWidth: workflowType === 'custom_period' ? '800px' : '500px',
              maxHeight: '90vh',
              overflow: 'auto',
              padding: 0
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div style={{
              padding: '20px',
              borderBottom: '1px solid #e9ecef',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: 'white'
            }}>
              <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 600 }}>
                {workflowType === 'custom_period' 
                  ? '📅 Análisis Personalizado por Período' 
                  : workflowType === 'entity_search' 
                  ? '🔍 Búsqueda de Entidades' 
                  : 'Configurar Workflow'}
              </h2>
              <button
                onClick={() => {
                  setModalOpen(false);
                  setWorkflowType('');
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '24px',
                  cursor: 'pointer',
                  color: '#868e96',
                  padding: '0 8px'
                }}
              >
                ×
              </button>
            </div>
            
            {/* Body */}
            <div style={{ 
              padding: '20px',
              backgroundColor: 'white'
            }}>
          
          {workflowType === 'custom_period' && (
            <div style={{ padding: '0' }}>
              <Stack gap="md">
            <Paper p="sm" style={{ backgroundColor: '#f8f9fa' }}>
              <Text size="sm" c="dimmed">
                <strong>Análisis por Período Personalizado:</strong> Selecciona el rango temporal y el tipo de análisis.
                Los agentes procesarán todos los documentos del período seleccionado y generarán insights detallados.
              </Text>
            </Paper>

            <Select
              label="Tipo de Análisis"
              description="Selecciona qué tipo de análisis deseas ejecutar"
              data={[
                { value: 'trend_analysis', label: '📈 Análisis de Tendencias - Evolución temporal completa' },
                { value: 'monthly_summary', label: '📅 Resumen de Período - Estadísticas agregadas' },
                { value: 'analyze_high_risk', label: '🔴 Detección de Alto Riesgo - Casos críticos' }
              ]}
              value={analysisType}
              onChange={(value) => setAnalysisType(value || 'trend_analysis')}
              styles={{
                dropdown: {
                  zIndex: 10000
                }
              }}
            />

            <Group grow>
              <NumberInput
                label="Año Inicio"
                min={2020}
                max={2025}
                value={startYear}
                onChange={(value) => setStartYear(Number(value))}
              />
              <Select
                label="Mes Inicio"
                data={[
                  { value: '1', label: 'Enero' },
                  { value: '2', label: 'Febrero' },
                  { value: '3', label: 'Marzo' },
                  { value: '4', label: 'Abril' },
                  { value: '5', label: 'Mayo' },
                  { value: '6', label: 'Junio' },
                  { value: '7', label: 'Julio' },
                  { value: '8', label: 'Agosto' },
                  { value: '9', label: 'Septiembre' },
                  { value: '10', label: 'Octubre' },
                  { value: '11', label: 'Noviembre' },
                  { value: '12', label: 'Diciembre' }
                ]}
                value={String(startMonth)}
                onChange={(value) => setStartMonth(Number(value))}
                styles={{
                  dropdown: {
                    zIndex: 10000
                  }
                }}
              />
            </Group>

            {analysisType === 'trend_analysis' && (
              <Group grow>
                <NumberInput
                  label="Año Fin"
                  min={2020}
                  max={2025}
                  value={endYear}
                  onChange={(value) => setEndYear(Number(value))}
                />
                <Select
                  label="Mes Fin"
                  data={[
                    { value: '1', label: 'Enero' },
                    { value: '2', label: 'Febrero' },
                    { value: '3', label: 'Marzo' },
                    { value: '4', label: 'Abril' },
                    { value: '5', label: 'Mayo' },
                    { value: '6', label: 'Junio' },
                    { value: '7', label: 'Julio' },
                    { value: '8', label: 'Agosto' },
                    { value: '9', label: 'Septiembre' },
                    { value: '10', label: 'Octubre' },
                    { value: '11', label: 'Noviembre' },
                    { value: '12', label: 'Diciembre' }
                  ]}
                  value={String(endMonth)}
                  onChange={(value) => setEndMonth(Number(value))}
                  styles={{
                    dropdown: {
                      zIndex: 10000
                    }
                  }}
                />
              </Group>
            )}

            <Paper p="sm" style={{ backgroundColor: '#e7f5ff', borderLeft: '3px solid #228be6' }}>
              <Text size="sm" fw={500}>
                {analysisType === 'trend_analysis' 
                  ? `📊 Se analizará la evolución desde ${startMonth}/${startYear} hasta ${endMonth}/${endYear}`
                  : `📊 Se analizará el período ${startMonth}/${startYear}`
                }
              </Text>
            </Paper>

            <Button 
              fullWidth 
              size="md"
              loading={loading}
              onClick={() => {
                const params = analysisType === 'trend_analysis'
                  ? { start_year: startYear, start_month: startMonth, end_year: endYear, end_month: endMonth }
                  : analysisType === 'monthly_summary'
                  ? { year: startYear, month: startMonth }
                  : { threshold: 50, limit: 20 };
                
                startWorkflow(analysisType, params);
              }}
            >
              🚀 Iniciar Análisis Personalizado
            </Button>
          </Stack>
            </div>
          )}

          {workflowType === 'entity_search' && (
            <div style={{ padding: '0' }}>
              <Stack gap="md">
            <Paper p="sm" style={{ backgroundColor: '#f8f9fa' }}>
              <Text size="sm" c="dimmed">
                <strong>Búsqueda de Entidades:</strong> Busca beneficiarios, organismos o entidades específicas en todos los documentos analizados.
              </Text>
            </Paper>

            <TextInput
              label="Entidad a buscar"
              placeholder="Ej: Municipalidad, Ministerio, Empresa..."
              description="Deja vacío para ver las entidades más frecuentes"
            />
            
            <Select
              label="Tipo de entidad"
              description="Selecciona qué tipo de entidad deseas buscar"
              data={[
                { value: 'beneficiaries', label: '👥 Beneficiarios - Personas o empresas que reciben fondos' },
                { value: 'amounts', label: '💰 Montos - Valores monetarios detectados' },
                { value: 'contracts', label: '📄 Contratos - Acuerdos y licitaciones' }
              ]}
              defaultValue="beneficiaries"
              styles={{
                dropdown: {
                  zIndex: 10000
                }
              }}
            />
            
            <Button 
              fullWidth 
              size="md"
              loading={loading}
              onClick={() => startWorkflow('entity_search', { entity_type: 'beneficiaries', entity_value: 'Municipalidad' })}
            >
              🔍 Buscar Entidades
            </Button>
          </Stack>
            </div>
          )}
            </div>
          </div>
        </>
      )}
    </>
  );
}

function SimpleGrid({ children, cols, spacing }: any) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: typeof cols === 'object' ? `repeat(${cols.base}, 1fr)` : `repeat(${cols}, 1fr)`,
      gap: spacing === 'md' ? '1rem' : spacing
    }}>
      {children}
    </div>
  );
}


