import { useState } from 'react';
import {
  Modal,
  Stepper,
  Button,
  Group,
  Text,
  Stack,
  Title,
  List,
  ThemeIcon,
  Image,
  Badge,
  Paper,
  Alert,
} from '@mantine/core';
import {
  IconShieldCheck,
  IconSearch,
  IconAlertTriangle,
  IconGraph,
  IconRobot,
  IconCheck,
  IconInfoCircle,
  IconMapPin,
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';

interface OnboardingWizardProps {
  opened: boolean;
  onClose: () => void;
}

export function OnboardingWizard({ opened, onClose }: OnboardingWizardProps) {
  const [active, setActive] = useState(0);
  const navigate = useNavigate();

  const nextStep = () => setActive((current) => (current < 5 ? current + 1 : current));
  const prevStep = () => setActive((current) => (current > 0 ? current - 1 : current));

  const handleFinish = () => {
    // Mark onboarding as completed in localStorage
    localStorage.setItem('onboarding_completed', 'true');
    onClose();
  };

  const handleNavigateAndClose = (path: string) => {
    navigate(path);
    handleFinish();
  };

  return (
    <Modal
      opened={opened}
      onClose={handleFinish}
      title={<Title order={2}>Bienvenido a Watcher Agent</Title>}
      size="lg"
      centered
    >
      <Stepper active={active} onStepClick={setActive}>
        {/* Step 1: ¿Qué es Watcher? */}
        <Stepper.Step label="Introducción" description="¿Qué es Watcher?">
          <Stack gap="md">
            <Alert icon={<IconInfoCircle size="1rem" />} variant="light" color="blue">
              <Text fw={600} mb="xs">
                Sistema de Monitoreo de Transparencia Fiscal
              </Text>
              <Text size="sm">
                Watcher Agent es tu herramienta para vigilar el cumplimiento de obligaciones de transparencia del
                gobierno provincial y municipal de Córdoba.
              </Text>
            </Alert>

            <div>
              <Text fw={600} mb="sm">
                ¿Por qué existe Watcher?
              </Text>
              <List spacing="sm" size="sm" icon={<ThemeIcon size={20} radius="xl" color="blue"><IconCheck size="0.9rem" /></ThemeIcon>}>
                <List.Item>
                  Los boletines oficiales contienen información crítica sobre decisiones gubernamentales, pero son
                  extensos y técnicos (100-300 páginas diarias)
                </List.Item>
                <List.Item>
                  La ley obliga a publicar información fiscal (presupuesto, ejecución, deuda, empleo público) pero
                  muchas veces no se cumple
                </List.Item>
                <List.Item>
                  Sin herramientas automatizadas, es imposible para un ciudadano común ejercer control efectivo
                </List.Item>
              </List>
            </div>

            <Paper p="md" withBorder bg="blue.0">
              <Text size="sm" fw={600} mb="xs">
                La misión de Watcher:
              </Text>
              <Text size="sm">
                Automatizar el monitoreo ciudadano, haciendo visible lo que debería estar publicado y alertando sobre
                irregularidades o incumplimientos legales.
              </Text>
            </Paper>
          </Stack>
        </Stepper.Step>

        {/* Step 2: Compliance Scorecard */}
        <Stepper.Step label="Compliance" description="Verificación legal" icon={<IconShieldCheck size="1.2rem" />}>
          <Stack gap="md">
            <ThemeIcon size="xl" variant="light" color="blue" radius="xl">
              <IconShieldCheck size="2rem" />
            </ThemeIcon>

            <div>
              <Title order={3} mb="sm">
                Scorecard de Compliance Fiscal
              </Title>
              <Text size="sm" mb="md">
                El corazón de Watcher: verifica si el gobierno cumple con las leyes de transparencia fiscal.
              </Text>
            </div>

            <div>
              <Text fw={600} mb="xs">
                ¿Qué verifica?
              </Text>
              <List spacing="sm" size="sm">
                <List.Item>
                  <strong>Presupuesto Anual:</strong> ¿Está publicado el presupuesto aprobado?
                </List.Item>
                <List.Item>
                  <strong>Ejecución Trimestral:</strong> ¿Publican cada 3 meses cuánto gastaron realmente?
                </List.Item>
                <List.Item>
                  <strong>Deuda Pública:</strong> ¿Informan cuánto deben, incluyendo deuda flotante?
                </List.Item>
                <List.Item>
                  <strong>Servicios de Deuda:</strong> ¿Detallan a quién le están pagando intereses?
                </List.Item>
                <List.Item>
                  <strong>Empleo Público:</strong> ¿Publican cuántas personas trabajan para el Estado?
                </List.Item>
              </List>
            </div>

            <Badge size="lg" variant="light">
              Base legal: Ley 25.917 (Federal) + Ley 10.471 (Córdoba)
            </Badge>

            <Button onClick={() => handleNavigateAndClose('/compliance')} fullWidth leftSection={<IconShieldCheck size="1rem" />}>
              Ver Scorecard de Compliance
            </Button>
          </Stack>
        </Stepper.Step>

        {/* Step 3: Análisis de Documentos */}
        <Stepper.Step label="Documentos" description="Análisis con IA" icon={<IconRobot size="1.2rem" />}>
          <Stack gap="md">
            <ThemeIcon size="xl" variant="light" color="teal" radius="xl">
              <IconRobot size="2rem" />
            </ThemeIcon>

            <div>
              <Title order={3} mb="sm">
                Análisis Inteligente de Documentos
              </Title>
              <Text size="sm" mb="md">
                Watcher descarga y procesa automáticamente boletines oficiales usando inteligencia artificial.
              </Text>
            </div>

            <div>
              <Text fw={600} mb="xs">
                ¿Qué hace el sistema?
              </Text>
              <List spacing="sm" size="sm">
                <List.Item>
                  <strong>Descarga automática:</strong> 300+ boletines oficiales procesados (2024-2026)
                </List.Item>
                <List.Item>
                  <strong>Extracción de texto:</strong> Convierte PDFs complejos en texto estructurado
                </List.Item>
                <List.Item>
                  <strong>Análisis con GPT-4:</strong> Identifica actos administrativos, montos, beneficiarios
                </List.Item>
                <List.Item>
                  <strong>Detección de patrones:</strong> Encuentra irregularidades y comportamientos sospechosos
                </List.Item>
              </List>
            </div>

            <Group grow>
              <Button onClick={() => handleNavigateAndClose('/documentos')} variant="light">
                Ver Documentos
              </Button>
              <Button onClick={() => handleNavigateAndClose('/wizard')} variant="light">
                Procesar Boletines
              </Button>
            </Group>
          </Stack>
        </Stepper.Step>

        {/* Step 4: Alertas y Red Flags */}
        <Stepper.Step label="Alertas" description="Detección de riesgos" icon={<IconAlertTriangle size="1.2rem" />}>
          <Stack gap="md">
            <ThemeIcon size="xl" variant="light" color="orange" radius="xl">
              <IconAlertTriangle size="2rem" />
            </ThemeIcon>

            <div>
              <Title order={3} mb="sm">
                Sistema de Alertas Automáticas
              </Title>
              <Text size="sm" mb="md">
                Watcher genera alertas cuando detecta situaciones que merecen atención ciudadana.
              </Text>
            </div>

            <div>
              <Text fw={600} mb="xs">
                Tipos de alertas:
              </Text>
              <List spacing="sm" size="sm">
                <List.Item>
                  <strong>Montos inusuales:</strong> Gastos significativamente mayores al promedio
                </List.Item>
                <List.Item>
                  <strong>Falta de información:</strong> Actos sin beneficiarios claros o montos ocultos
                </List.Item>
                <List.Item>
                  <strong>Concentración:</strong> Demasiado dinero yendo a pocos beneficiarios
                </List.Item>
                <List.Item>
                  <strong>Desvíos presupuestarios:</strong> Ejecución muy por encima o debajo de lo planificado
                </List.Item>
                <List.Item>
                  <strong>Incumplimientos:</strong> Obligaciones legales no cumplidas
                </List.Item>
              </List>
            </div>

            <Button onClick={() => handleNavigateAndClose('/alertas')} fullWidth leftSection={<IconAlertTriangle size="1rem" />}>
              Ver Alertas Activas
            </Button>
          </Stack>
        </Stepper.Step>

        {/* Step 5: Búsqueda y Exploración */}
        <Stepper.Step label="Herramientas" description="Explora los datos" icon={<IconSearch size="1.2rem" />}>
          <Stack gap="md">
            <ThemeIcon size="xl" variant="light" color="violet" radius="xl">
              <IconGraph size="2rem" />
            </ThemeIcon>

            <div>
              <Title order={3} mb="sm">
                Herramientas de Exploración
              </Title>
              <Text size="sm" mb="md">
                Watcher te da herramientas poderosas para investigar y entender los datos.
              </Text>
            </div>

            <Stack gap="xs">
              <Paper p="sm" withBorder>
                <Group>
                  <ThemeIcon variant="light" color="violet">
                    <IconSearch size="1rem" />
                  </ThemeIcon>
                  <div style={{ flex: 1 }}>
                    <Text fw={600} size="sm">
                      Búsqueda Semántica
                    </Text>
                    <Text size="xs" c="dimmed">
                      Busca por conceptos, no solo palabras exactas
                    </Text>
                  </div>
                </Group>
              </Paper>

              <Paper p="sm" withBorder>
                <Group>
                  <ThemeIcon variant="light" color="teal">
                    <IconGraph size="1rem" />
                  </ThemeIcon>
                  <div style={{ flex: 1 }}>
                    <Text fw={600} size="sm">
                      Grafo de Conocimiento
                    </Text>
                    <Text size="xs" c="dimmed">
                      Visualiza relaciones entre organismos, empresas y personas
                    </Text>
                  </div>
                </Group>
              </Paper>

              <Paper p="sm" withBorder>
                <Group>
                  <ThemeIcon variant="light" color="blue">
                    <IconMapPin size="1rem" />
                  </ThemeIcon>
                  <div style={{ flex: 1 }}>
                    <Text fw={600} size="sm">
                      Vista por Jurisdicciones
                    </Text>
                    <Text size="xs" c="dimmed">
                      Filtra por provincia, capital, municipalidades o comunas
                    </Text>
                  </div>
                </Group>
              </Paper>
            </Stack>

            <Group grow>
              <Button onClick={() => handleNavigateAndClose('/search')} variant="light">
                Búsqueda
              </Button>
              <Button onClick={() => handleNavigateAndClose('/knowledge-graph')} variant="light">
                Grafo
              </Button>
            </Group>
          </Stack>
        </Stepper.Step>

        {/* Step 6: Finalizació n */}
        <Stepper.Completed>
          <Stack gap="md" align="center">
            <ThemeIcon size={80} radius={80} variant="light" color="green">
              <IconCheck size="3rem" />
            </ThemeIcon>

            <Title order={2} ta="center">
              ¡Listo para comenzar!
            </Title>

            <Text size="sm" ta="center" c="dimmed">
              Ya conoces las herramientas principales de Watcher Agent. Ahora puedes empezar a explorar y ejercer
              control ciudadano sobre la transparencia fiscal.
            </Text>

            <Alert icon={<IconInfoCircle size="1rem" />} variant="light" color="blue">
              <Text size="sm">
                <strong>Tip:</strong> Comienza visitando el Scorecard de Compliance para ver qué obligaciones legales
                se están cumpliendo y cuáles no. Es la forma más rápida de entender el estado general de la
                transparencia fiscal.
              </Text>
            </Alert>

            <Button onClick={handleFinish} size="lg" fullWidth>
              Comenzar a usar Watcher
            </Button>
          </Stack>
        </Stepper.Completed>
      </Stepper>

      <Group justify="space-between" mt="xl">
        {active < 5 && (
          <>
            <Button variant="default" onClick={prevStep} disabled={active === 0}>
              Anterior
            </Button>
            <Button onClick={nextStep}>{active === 4 ? 'Finalizar' : 'Siguiente'}</Button>
          </>
        )}
      </Group>
    </Modal>
  );
}

// Hook to check if onboarding should be shown
export function useOnboarding() {
  const [shouldShow, setShouldShow] = useState(false);

  const checkOnboarding = () => {
    const completed = localStorage.getItem('onboarding_completed');
    if (!completed) {
      setShouldShow(true);
    }
  };

  const resetOnboarding = () => {
    localStorage.removeItem('onboarding_completed');
    setShouldShow(true);
  };

  return {
    shouldShow,
    checkOnboarding,
    resetOnboarding,
    setShouldShow,
  };
}
