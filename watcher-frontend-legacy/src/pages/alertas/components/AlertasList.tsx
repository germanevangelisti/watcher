import { SimpleGrid, Pagination, Group, Text } from '@mantine/core';
import { useState } from 'react';
import { AlertCard } from '../../../components/shared/AlertCard';
import type { Alerta } from '../../../types/alertas';

interface AlertasListProps {
  alertas: Alerta[];
  onViewDetails: (id: number) => void;
}

export function AlertasList({ alertas, onViewDetails }: AlertasListProps) {
  const [page, setPage] = useState(1);
  const pageSize = 9;
  const totalPages = Math.ceil(alertas.length / pageSize);
  const startIndex = (page - 1) * pageSize;
  const paginatedAlertas = alertas.slice(startIndex, startIndex + pageSize);

  if (alertas.length === 0) {
    return (
      <Text c="dimmed" ta="center" py="xl">
        No se encontraron alertas con los filtros seleccionados
      </Text>
    );
  }

  return (
    <>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
        {paginatedAlertas.map((alerta) => (
          <AlertCard
            key={alerta.id}
            titulo={alerta.titulo}
            descripcion={alerta.descripcion}
            severidad={alerta.nivel_severidad}
            tipo={alerta.tipo_alerta}
            organismo={alerta.organismo}
            fecha={alerta.fecha_deteccion}
            accionesSugeridas={
              alerta.acciones_sugeridas 
                ? Object.values(alerta.acciones_sugeridas) 
                : []
            }
            valorDetectado={alerta.valor_detectado}
            valorEsperado={alerta.valor_esperado}
            onViewDetails={() => onViewDetails(alerta.id)}
          />
        ))}
      </SimpleGrid>

      {totalPages > 1 && (
        <Group justify="center" mt="xl">
          <Pagination 
            total={totalPages} 
            value={page} 
            onChange={setPage}
          />
        </Group>
      )}
    </>
  );
}

