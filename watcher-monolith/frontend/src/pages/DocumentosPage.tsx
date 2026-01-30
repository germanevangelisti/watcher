import { Container, Title, Text, Tabs } from '@mantine/core';
import { IconFileText, IconFileDescription, IconSearch } from '@tabler/icons-react';
import { useState } from 'react';
import { BoletinesTab } from './documentos/BoletinesTab';
import { ActosTab } from './documentos/ActosTab';

export function DocumentosPage() {
  const [activeTab, setActiveTab] = useState<string | null>('boletines');

  return (
    <Container size="xl" py="xl">
      <Title order={2} mb="xs">📄 Documentos</Title>
      <Text c="dimmed" mb="xl">
        Boletines oficiales y actos administrativos extraídos
      </Text>

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List>
          <Tabs.Tab value="boletines" leftSection={<IconFileText size={16} />}>
            Boletines Oficiales
          </Tabs.Tab>
          <Tabs.Tab value="actos" leftSection={<IconFileDescription size={16} />}>
            Actos Administrativos
          </Tabs.Tab>
          <Tabs.Tab value="buscar" leftSection={<IconSearch size={16} />}>
            Búsqueda Avanzada
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="boletines" pt="xl">
          <BoletinesTab />
        </Tabs.Panel>

        <Tabs.Panel value="actos" pt="xl">
          <ActosTab />
        </Tabs.Panel>

        <Tabs.Panel value="buscar" pt="xl">
          <Text c="dimmed" ta="center" py="xl">
            🔍 Búsqueda semántica avanzada próximamente
          </Text>
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}


