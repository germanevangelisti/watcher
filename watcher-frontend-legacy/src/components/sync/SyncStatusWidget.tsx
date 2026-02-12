import React, { useState, useEffect } from 'react';
import {
  Group,
  Text,
  Badge,
  Tooltip,
  ActionIcon,
  Indicator,
  Stack
} from '@mantine/core';
import {
  IconRefresh,
  IconCheck,
  IconAlertCircle,
  IconClock,
  IconDownload
} from '@tabler/icons-react';
import axios from 'axios';

const API_BASE = 'http://localhost:8001/api/v1/sync';

interface SyncStatus {
  status: string;
  last_detected_date: string | null;
  boletines_pending: number;
  is_syncing: boolean;
}

interface SyncStatusWidgetProps {
  onClick?: () => void;
  showDetails?: boolean;
}

const SyncStatusWidget: React.FC<SyncStatusWidgetProps> = ({ 
  onClick, 
  showDetails = true 
}) => {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const loadStatus = async () => {
    try {
      const response = await axios.get(API_BASE + '/status');
      setStatus(response.data);
    } catch (error) {
      console.error('Error loading sync status:', error);
    }
  };

  useEffect(() => {
    loadStatus();
    
    // Auto-refresh cada 30 segundos
    const interval = setInterval(loadStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // Si está sincronizando, actualizar más frecuentemente
  useEffect(() => {
    if (status?.is_syncing) {
      const interval = setInterval(loadStatus, 5000);
      return () => clearInterval(interval);
    }
  }, [status?.is_syncing]);

  const handleRefresh = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setLoading(true);
    await loadStatus();
    setLoading(false);
  };

  if (!status) {
    return null;
  }

  const getIndicatorColor = () => {
    if (status.is_syncing) return 'blue';
    if (status.boletines_pending > 0) return 'orange';
    return 'green';
  };

  const getStatusIcon = () => {
    if (status.is_syncing) return <IconDownload size={16} />;
    if (status.boletines_pending > 0) return <IconClock size={16} />;
    return <IconCheck size={16} />;
  };

  const getStatusText = () => {
    if (status.is_syncing) return 'Sincronizando...';
    if (status.boletines_pending > 0) {
      return `${status.boletines_pending} pendiente${status.boletines_pending > 1 ? 's' : ''}`;
    }
    return 'Actualizado';
  };

  const getDateText = () => {
    if (!status.last_detected_date) return 'Sin datos';
    
    const date = new Date(status.last_detected_date);
    const today = new Date();
    const diffTime = Math.abs(today.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Hoy';
    if (diffDays === 1) return 'Ayer';
    if (diffDays < 7) return `Hace ${diffDays} días`;
    
    return date.toLocaleDateString('es-AR', { 
      day: 'numeric', 
      month: 'short',
      year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
    });
  };

  return (
    <Tooltip
      label={
        <Stack gap={4}>
          <Text size="xs" fw={600}>Estado de Sincronización</Text>
          <Text size="xs">Última fecha: {getDateText()}</Text>
          {status.boletines_pending > 0 && (
            <Text size="xs" c="orange">{status.boletines_pending} boletines pendientes</Text>
          )}
          <Text size="xs" c="dimmed">Click para ver detalles</Text>
        </Stack>
      }
      position="bottom"
      withArrow
    >
      <Group 
        gap="xs" 
        style={{ cursor: onClick ? 'pointer' : 'default' }}
        onClick={onClick}
      >
        <Indicator 
          color={getIndicatorColor()} 
          processing={status.is_syncing}
          size={10}
        >
          <ActionIcon 
            variant="subtle" 
            size="lg"
            loading={loading}
            onClick={handleRefresh}
          >
            <IconRefresh size={18} />
          </ActionIcon>
        </Indicator>

        {showDetails && (
          <div>
            <Text size="xs" c="dimmed">Sync</Text>
            <Group gap={4}>
              {getStatusIcon()}
              <Text size="sm" fw={500}>{getStatusText()}</Text>
            </Group>
          </div>
        )}
      </Group>
    </Tooltip>
  );
};

export default SyncStatusWidget;
