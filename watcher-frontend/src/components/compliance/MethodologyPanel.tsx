import { Accordion, Text, Stack, Badge, Group, ThemeIcon, Code, List } from '@mantine/core';
import {
  IconMathFunction,
  IconShieldCheck,
  IconShieldHalf,
  IconShieldX,
  IconScale,
  IconChartBar,
} from '@tabler/icons-react';

export function MethodologyPanel() {
  return (
    <Accordion variant="separated">
      <Accordion.Item value="scoring">
        <Accordion.Control icon={<IconMathFunction size="1rem" />}>
          ¿Cómo se calcula el Score de Compliance?
        </Accordion.Control>
        <Accordion.Panel>
          <Stack gap="md">
            <Text size="sm">
              El score de compliance se calcula mediante una fórmula de promedio ponderado que considera la prioridad
              de cada obligación legal:
            </Text>

            <Code block>
              {`Score = Σ(weight_i × value_i) / Σ(weight_i) × 100

Donde:
- weight_i = peso del check (Critical: 3.0, High: 2.0, Medium: 1.0, Low: 0.5)
- value_i = valor según estado (PASS: 1.0, WARN: 0.5, FAIL: 0.0, UNKNOWN: no suma)`}
            </Code>

            <div>
              <Text size="sm" fw={600} mb={5}>
                Pesos por Prioridad:
              </Text>
              <Stack gap="xs">
                <Group>
                  <Badge color="red">CRÍTICO</Badge>
                  <Text size="sm">Peso: 3.0 - Obligaciones esenciales de transparencia fiscal</Text>
                </Group>
                <Group>
                  <Badge color="orange">ALTO</Badge>
                  <Text size="sm">Peso: 2.0 - Obligaciones importantes con impacto significativo</Text>
                </Group>
                <Group>
                  <Badge color="yellow">MEDIO</Badge>
                  <Text size="sm">Peso: 1.0 - Obligaciones de seguimiento regular</Text>
                </Group>
                <Group>
                  <Badge color="blue">BAJO</Badge>
                  <Text size="sm">Peso: 0.5 - Obligaciones complementarias</Text>
                </Group>
              </Stack>
            </div>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="states">
        <Accordion.Control icon={<IconScale size="1rem" />}>¿Qué significa cada estado?</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="md">
            <Group>
              <ThemeIcon color="green" variant="light">
                <IconShieldCheck size="1rem" />
              </ThemeIcon>
              <div style={{ flex: 1 }}>
                <Text fw={600} size="sm">
                  PASS (Cumple) - Valor: 1.0
                </Text>
                <Text size="sm" c="dimmed">
                  La obligación legal se cumple completamente. La información requerida está publicada, es accesible y
                  cumple con todos los requisitos (periodicidad, rezago, formato, contenido).
                </Text>
              </div>
            </Group>

            <Group>
              <ThemeIcon color="yellow" variant="light">
                <IconShieldHalf size="1rem" />
              </ThemeIcon>
              <div style={{ flex: 1 }}>
                <Text fw={600} size="sm">
                  WARN (Cumple Parcialmente) - Valor: 0.5
                </Text>
                <Text size="sm" c="dimmed">
                  La obligación se cumple parcialmente. Puede faltar algún requisito secundario (ej: publicar ejecución
                  en base devengado pero no en base caja, o exceder ligeramente el rezago permitido).
                </Text>
              </div>
            </Group>

            <Group>
              <ThemeIcon color="red" variant="light">
                <IconShieldX size="1rem" />
              </ThemeIcon>
              <div style={{ flex: 1 }}>
                <Text fw={600} size="sm">
                  FAIL (No Cumple) - Valor: 0.0
                </Text>
                <Text size="sm" c="dimmed">
                  La obligación legal no se cumple. La información requerida no está publicada, no es accesible, o no
                  cumple con requisitos críticos (ej: faltan 2+ trimestres de ejecución presupuestaria).
                </Text>
              </div>
            </Group>

            <Group>
              <ThemeIcon color="gray" variant="light">
                <IconShieldX size="1rem" />
              </ThemeIcon>
              <div style={{ flex: 1 }}>
                <Text fw={600} size="sm">
                  UNKNOWN (Sin Evaluar) - No suma al score
                </Text>
                <Text size="sm" c="dimmed">
                  El check aún no ha sido evaluado o no se pudo determinar su estado. No se considera en el cálculo del
                  score para no penalizar ni beneficiar artificialmente.
                </Text>
              </div>
            </Group>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="levels">
        <Accordion.Control icon={<IconChartBar size="1rem" />}>
          Niveles de Compliance
        </Accordion.Control>
        <Accordion.Panel>
          <Stack gap="sm">
            <Text size="sm" mb="xs">
              Según el score calculado, el nivel de compliance se clasifica en:
            </Text>

            <Group>
              <Badge size="lg" color="green">
                EXCELENTE
              </Badge>
              <Text size="sm">90% - 100%: Cumplimiento ejemplar de obligaciones fiscales</Text>
            </Group>

            <Group>
              <Badge size="lg" color="teal">
                BUENO
              </Badge>
              <Text size="sm">75% - 89%: Cumplimiento satisfactorio con áreas menores de mejora</Text>
            </Group>

            <Group>
              <Badge size="lg" color="yellow">
                ACEPTABLE
              </Badge>
              <Text size="sm">50% - 74%: Cumplimiento básico con deficiencias significativas</Text>
            </Group>

            <Group>
              <Badge size="lg" color="red">
                DEFICIENTE
              </Badge>
              <Text size="sm">0% - 49%: Incumplimiento grave de obligaciones legales</Text>
            </Group>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>

      <Accordion.Item value="validation">
        <Accordion.Control icon={<IconScale size="1rem" />}>Proceso de Validación</Accordion.Control>
        <Accordion.Panel>
          <Stack gap="md">
            <Text size="sm">
              Cada check de compliance se valida mediante un proceso sistemático de 5 pasos:
            </Text>

            <List size="sm" spacing="md">
              <List.Item>
                <Text fw={600}>1. Discovery</Text>
                <Text size="sm" c="dimmed">
                  Búsqueda de evidencia en las fuentes oficiales configuradas (portales web de la provincia)
                </Text>
              </List.Item>

              <List.Item>
                <Text fw={600}>2. Extraction</Text>
                <Text size="sm" c="dimmed">
                  Extracción y normalización de datos (PDFs, tablas HTML, archivos descargables)
                </Text>
              </List.Item>

              <List.Item>
                <Text fw={600}>3. Validation</Text>
                <Text size="sm" c="dimmed">
                  Aplicación de reglas de validación específicas del check (periodicidad, rezago, campos requeridos)
                </Text>
              </List.Item>

              <List.Item>
                <Text fw={600}>4. Evidence Storage</Text>
                <Text size="sm" c="dimmed">
                  Almacenamiento de evidencia con snapshot y hash para reproducibilidad
                </Text>
              </List.Item>

              <List.Item>
                <Text fw={600}>5. Status Assignment</Text>
                <Text size="sm" c="dimmed">
                  Asignación de estado (PASS/WARN/FAIL) según resultados de validación
                </Text>
              </List.Item>
            </List>

            <Text size="sm" c="dimmed" style={{ fontStyle: 'italic' }}>
              Nota: Este proceso garantiza que cada evaluación sea auditable y reproducible, permitiendo verificar
              cómo se llegó a cada conclusión.
            </Text>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  );
}
