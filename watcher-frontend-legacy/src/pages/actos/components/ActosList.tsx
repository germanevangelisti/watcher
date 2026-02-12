import { SimpleGrid, Pagination, Group, Text } from '@mantine/core';
import { useState } from 'react';
import { ActoCard } from '../../../components/shared/ActoCard';
import type { Acto } from '../../../types/actos';

interface ActosListProps {
  actos: Acto[];
  onViewDetails: (id: number) => void;
}

export function ActosList({ actos, onViewDetails }: ActosListProps) {
  const [page, setPage] = useState(1);
  const pageSize = 9;
  const totalPages = Math.ceil(actos.length / pageSize);
  const startIndex = (page - 1) * pageSize;
  const paginatedActos = actos.slice(startIndex, startIndex + pageSize);

  if (actos.length === 0) {
    return (
      <Text c="dimmed" ta="center" py="xl">
        No se encontraron actos con los filtros seleccionados
      </Text>
    );
  }

  return (
    <>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
        {paginatedActos.map((acto) => (
          <ActoCard
            key={acto.id}
            tipo={acto.tipo_acto}
            numero={acto.numero}
            organismo={acto.organismo}
            monto={acto.monto}
            riesgo={acto.nivel_riesgo}
            descripcion={acto.descripcion}
            fecha={acto.fecha}
            onViewDetails={() => onViewDetails(acto.id)}
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

