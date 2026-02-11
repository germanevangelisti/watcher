import { MantineProvider } from '@mantine/core';
import { DatesProvider } from '@mantine/dates';
import { Notifications } from '@mantine/notifications';
import { BrowserRouter } from 'react-router-dom';
import { useEffect } from 'react';
import { AppShell } from './components/layout/AppShell';
import { AppRoutes } from './routes';
import { UserModeProvider } from './contexts/UserModeContext';
import { OnboardingWizard, useOnboarding } from './components/onboarding/OnboardingWizard';
import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/notifications/styles.css';

function AppContent() {
  const { shouldShow, checkOnboarding, setShouldShow } = useOnboarding();

  useEffect(() => {
    // Check onboarding on first mount
    checkOnboarding();
  }, []);

  return (
    <>
      <AppShell>
        <AppRoutes />
      </AppShell>
      <OnboardingWizard opened={shouldShow} onClose={() => setShouldShow(false)} />
    </>
  );
}

function App() {
  return (
    <MantineProvider>
      <Notifications />
      <DatesProvider settings={{ locale: 'es', firstDayOfWeek: 0 }}>
        <UserModeProvider>
          <BrowserRouter>
            <AppContent />
          </BrowserRouter>
        </UserModeProvider>
      </DatesProvider>
    </MantineProvider>
  );
}

export default App;