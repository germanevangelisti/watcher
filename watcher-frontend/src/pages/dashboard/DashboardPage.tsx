import { RealDashboard } from './RealDashboard';

export function DashboardPage() {
  return <RealDashboard />;
}

export function OldDashboardPage() {
  const { isCiudadano } = useUserMode();
  const [metricas, setMetricas] = useState<MetricasGeneralesType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadMetricas();
  }, []);

  const loadMetricas = async () => {
    try {
      setLoading(true);
      setError('');
      
      const data = await getMetricasGenerales();
      setMetricas(data);
    } catch (err) {
      setError('Error cargando métricas: ' + (err as Error).message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Container size="xl">
        <Group justify="center" py="xl">
          <Loader size="lg" />
        </Group>
      </Container>
    );
  }

  if (error || !metricas) {
    return (
      <Container size="xl">
        <Alert color="red" title="Error" icon={<IconAlertCircle size="1rem" />}>
          {error || 'No se pudieron cargar las métricas'}
        </Alert>
      </Container>
    );
  }

  // Calcular alertas destacadas
  const porcentajeRiesgo = metricas.total_actos > 0
    ? (metricas.actos_alto_riesgo / metricas.total_actos) * 100
    : 0;
  
  const alertas = [];
  if (metricas.alertas_criticas > 0) {
    alertas.push({
      type: 'critical',
      title: `${metricas.alertas_criticas} Alertas Críticas`,
      message: `Se detectaron ${metricas.alertas_criticas} alertas críticas que requieren atención inmediata.`,
      color: 'red',
      icon: IconAlertTriangle
    });
  }
  if (porcentajeRiesgo > 20) {
    alertas.push({
      type: 'warning',
      title: 'Alto Nivel de Riesgo',
      message: `El ${porcentajeRiesgo.toFixed(1)}% de los actos son de alto riesgo. Se recomienda revisión prioritaria.`,
      color: 'orange',
      icon: IconAlertTriangle
    });
  }
  if (metricas.porcentaje_ejecucion_global < 25 && metricas.porcentaje_ejecucion_global > 0) {
    alertas.push({
      type: 'info',
      title: 'Ejecución Presupuestaria Baja',
      message: `La ejecución presupuestaria es del ${metricas.porcentaje_ejecucion_global.toFixed(1)}%. Se recomienda revisar el avance.`,
      color: 'yellow',
      icon: IconInfoCircle
    });
  }

  return (
    <Container size="xl">
      <Stack gap="xl">
        {/* Header */}
        <Stack gap="md">
          <Group justify="space-between" align="flex-start">
            <div>
              <Title order={1} mb="xs">
                {isCiudadano ? 'Panel de Control' : 'Dashboard de Métricas Ejecutivas'}
              </Title>
              <Text size="lg" c="dimmed">
                {isCiudadano 
                  ? 'Resumen del estado de gestión fiscal' 
                  : 'Análisis integral de presupuesto, actos y alertas'}
              </Text>
            </div>
            <ModeToggle />
          </Group>
          
          {/* Timeline del año 2025 */}
          <Card withBorder shadow="sm" padding="md" style={{ backgroundColor: 'var(--mantine-color-gray-0)' }}>
            <YearTimeline />
          </Card>
        </Stack>

        {/* Resumen Ejecutivo */}
        <Card withBorder shadow="sm" padding="lg" style={{ backgroundColor: 'var(--mantine-color-blue-0)' }}>
          <Stack gap="md">
            <Group justify="space-between" align="center">
              <Title order={3}>Resumen Ejecutivo</Title>
              <Badge size="lg" variant="light" color="blue">
                Estado General
              </Badge>
            </Group>
            <Divider />
            <Grid>
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <div>
                  <Text size="xs" c="dimmed" mb={4}>Programas Activos</Text>
                  <Text size="xl" fw={700}>{metricas.total_programas.toLocaleString('es-AR')}</Text>
                </div>
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <div>
                  <Text size="xs" c="dimmed" mb={4}>Ejecución Presupuestaria</Text>
                  <Group gap="xs" align="center">
                    <Text size="xl" fw={700} c={metricas.porcentaje_ejecucion_global > 50 ? 'green' : 'orange'}>
                      {metricas.porcentaje_ejecucion_global.toFixed(1)}%
                    </Text>
                    {metricas.porcentaje_ejecucion_global > 50 && (
                      <IconTrendingUp size={20} style={{ color: 'var(--mantine-color-green-6)' }} />
                    )}
                  </Group>
                </div>
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <div>
                  <Text size="xs" c="dimmed" mb={4}>Actos de Alto Riesgo</Text>
                  <Group gap="xs" align="center">
                    <Text size="xl" fw={700} c="red">
                      {metricas.actos_alto_riesgo.toLocaleString('es-AR')}
                    </Text>
                    <Badge color="red" variant="light" size="sm">
                      {porcentajeRiesgo.toFixed(1)}%
                    </Badge>
                  </Group>
                </div>
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <div>
                  <Text size="xs" c="dimmed" mb={4}>Alertas Críticas</Text>
                  <Group gap="xs" align="center">
                    <Text size="xl" fw={700} c={metricas.alertas_criticas > 0 ? 'orange' : 'green'}>
                      {metricas.alertas_criticas.toLocaleString('es-AR')}
                    </Text>
                    {metricas.alertas_criticas > 0 && (
                      <IconAlertTriangle size={20} style={{ color: 'var(--mantine-color-orange-6)' }} />
                    )}
                  </Group>
                </div>
              </Grid.Col>
            </Grid>
          </Stack>
        </Card>

        {/* Alertas Destacadas */}
        {alertas.length > 0 && (
          <Stack gap="sm">
            {alertas.map((alerta, idx) => {
              const Icon = alerta.icon;
              return (
                <Alert
                  key={idx}
                  icon={<Icon size={16} />}
                  title={alerta.title}
                  color={alerta.color}
                  variant="light"
                >
                  {alerta.message}
                </Alert>
              );
            })}
          </Stack>
        )}

        {/* Métricas Generales */}
        <MetricasGenerales metricas={metricas} />

        {/* Charts Row */}
        <Grid>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <RiesgoChart metricas={metricas} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <EjecucionChart metricas={metricas} />
          </Grid.Col>
        </Grid>

        {/* Top Organismos */}
        <TopOrganismos metricas={metricas} />
      </Stack>
    </Container>
  );
}

