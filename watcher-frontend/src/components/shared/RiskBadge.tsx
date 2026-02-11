import { Badge } from '@mantine/core';
import { IconAlertTriangle, IconAlertCircle, IconInfoCircle } from '@tabler/icons-react';

interface RiskBadgeProps {
  risk: 'ALTO' | 'MEDIO' | 'BAJO' | 'CRITICO';
  size?: 'sm' | 'md' | 'lg';
}

export function RiskBadge({ risk, size = 'md' }: RiskBadgeProps) {
  const config = {
    CRITICO: { color: 'red', label: 'Crítico', icon: IconAlertTriangle },
    ALTO: { color: 'orange', label: 'Alto', icon: IconAlertCircle },
    MEDIO: { color: 'yellow', label: 'Medio', icon: IconAlertCircle },
    BAJO: { color: 'blue', label: 'Bajo', icon: IconInfoCircle },
  };

  const { color, label, icon: Icon } = config[risk] || config.BAJO;

  return (
    <Badge 
      color={color} 
      size={size}
      leftSection={<Icon size="0.9rem" />}
    >
      {label}
    </Badge>
  );
}

