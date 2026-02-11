import { Card, Text, Group, ThemeIcon, Anchor, Stack, Badge } from '@mantine/core';
import { IconBook, IconExternalLink } from '@tabler/icons-react';

interface LegalBasisCardProps {
  title: string;
  legal_basis: string;
  legal_text?: string;
  legal_url?: string;
  explanation?: string;
  variant?: 'default' | 'compact';
}

export function LegalBasisCard({
  title,
  legal_basis,
  legal_text,
  legal_url,
  explanation,
  variant = 'default',
}: LegalBasisCardProps) {
  if (variant === 'compact') {
    return (
      <Group gap="xs" wrap="nowrap">
        <ThemeIcon size="sm" variant="light" color="blue">
          <IconBook size="0.8rem" />
        </ThemeIcon>
        <div style={{ flex: 1 }}>
          <Text size="xs" c="dimmed">
            {legal_basis}
          </Text>
          {legal_url && (
            <Anchor href={legal_url} target="_blank" size="xs">
              Ver texto legal <IconExternalLink size="0.7rem" />
            </Anchor>
          )}
        </div>
      </Group>
    );
  }

  return (
    <Card padding="md" withBorder>
      <Stack gap="sm">
        <Group>
          <ThemeIcon size="lg" variant="light" color="blue">
            <IconBook size="1.2rem" />
          </ThemeIcon>
          <div style={{ flex: 1 }}>
            <Text fw={600}>{title}</Text>
            <Badge size="sm" variant="light" color="blue">
              {legal_basis}
            </Badge>
          </div>
        </Group>

        {legal_text && (
          <div>
            <Text size="sm" fw={500} mb={5}>
              Texto Legal:
            </Text>
            <Text size="sm" c="dimmed" style={{ fontStyle: 'italic' }}>
              "{legal_text}"
            </Text>
          </div>
        )}

        {explanation && (
          <div>
            <Text size="sm" fw={500} mb={5}>
              ¿Qué significa esto?
            </Text>
            <Text size="sm">{explanation}</Text>
          </div>
        )}

        {legal_url && (
          <Anchor href={legal_url} target="_blank" size="sm">
            Ver texto legal completo <IconExternalLink size="0.9rem" />
          </Anchor>
        )}
      </Stack>
    </Card>
  );
}
