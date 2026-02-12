import { Grid } from '@mantine/core';
import { IconAlertTriangle, IconAlertCircle, IconInfoCircle, IconCheck } from '@tabler/icons-react';
import { StatsCard } from '../../../components/shared/StatsCard';
import type { AlertasStats } from '../../../types/alertas';

interface AlertasStatsProps {
  stats: AlertasStats;
}

export function AlertasStatsComponent({ stats }: AlertasStatsProps) {
  return (
    <Grid>
      <Grid.Col span={{ base: 12, xs: 6, sm: 3 }}>
        <StatsCard
          title="Total Alertas"
          value={stats.total}
          icon={IconAlertCircle}
          color="blue"
        />
      </Grid.Col>
      
      <Grid.Col span={{ base: 12, xs: 6, sm: 3 }}>
        <StatsCard
          title="Críticas"
          value={stats.criticas}
          icon={IconAlertTriangle}
          color="red"
        />
      </Grid.Col>
      
      <Grid.Col span={{ base: 12, xs: 6, sm: 3 }}>
        <StatsCard
          title="Altas"
          value={stats.altas}
          icon={IconAlertCircle}
          color="orange"
        />
      </Grid.Col>
      
      <Grid.Col span={{ base: 12, xs: 6, sm: 3 }}>
        <StatsCard
          title="Activas"
          value={stats.activas}
          icon={IconCheck}
          color="green"
        />
      </Grid.Col>
    </Grid>
  );
}

