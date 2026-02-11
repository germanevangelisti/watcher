import { useState } from 'react';
import { Modal, Button, Text, Stack, Title, ThemeIcon, Group, Divider, List } from '@mantine/core';
import { IconInfoCircle, IconHelp } from '@tabler/icons-react';

interface ComplianceExplainerProps {
  title: string;
  why_important: string;
  what_to_look_for?: string[];
  consequences?: string[];
  example?: string;
  trigger?: React.ReactNode;
}

export function ComplianceExplainer({
  title,
  why_important,
  what_to_look_for,
  consequences,
  example,
  trigger,
}: ComplianceExplainerProps) {
  const [opened, setOpened] = useState(false);

  const defaultTrigger = (
    <Button
      variant="subtle"
      size="xs"
      leftSection={<IconHelp size="1rem" />}
      onClick={() => setOpened(true)}
    >
      ¿Por qué importa?
    </Button>
  );

  return (
    <>
      <div onClick={() => setOpened(true)} style={{ display: 'inline-block', cursor: 'pointer' }}>
        {trigger || defaultTrigger}
      </div>

      <Modal
        opened={opened}
        onClose={() => setOpened(false)}
        title={
          <Group>
            <ThemeIcon size="lg" variant="light" color="blue">
              <IconInfoCircle size="1.2rem" />
            </ThemeIcon>
            <Title order={3}>{title}</Title>
          </Group>
        }
        size="lg"
      >
        <Stack gap="md">
          <div>
            <Text fw={600} size="sm" mb={5}>
              ¿Por qué es importante?
            </Text>
            <Text size="sm">{why_important}</Text>
          </div>

          {what_to_look_for && what_to_look_for.length > 0 && (
            <>
              <Divider />
              <div>
                <Text fw={600} size="sm" mb={5}>
                  ¿Qué debes revisar?
                </Text>
                <List size="sm" spacing="xs">
                  {what_to_look_for.map((item, index) => (
                    <List.Item key={index}>{item}</List.Item>
                  ))}
                </List>
              </div>
            </>
          )}

          {consequences && consequences.length > 0 && (
            <>
              <Divider />
              <div>
                <Text fw={600} size="sm" mb={5} c="red">
                  Consecuencias del incumplimiento:
                </Text>
                <List size="sm" spacing="xs">
                  {consequences.map((item, index) => (
                    <List.Item key={index}>{item}</List.Item>
                  ))}
                </List>
              </div>
            </>
          )}

          {example && (
            <>
              <Divider />
              <div>
                <Text fw={600} size="sm" mb={5}>
                  Ejemplo:
                </Text>
                <Text size="sm" style={{ fontStyle: 'italic' }}>
                  {example}
                </Text>
              </div>
            </>
          )}

          <Button onClick={() => setOpened(false)} fullWidth mt="md">
            Entendido
          </Button>
        </Stack>
      </Modal>
    </>
  );
}
