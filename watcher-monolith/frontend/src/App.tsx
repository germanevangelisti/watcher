import { MantineProvider } from '@mantine/core';
import { DatesProvider } from '@mantine/dates';
import { Notifications } from '@mantine/notifications';
import { BrowserRouter } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { AppRoutes } from './routes';
import { UserModeProvider } from './contexts/UserModeContext';
import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/notifications/styles.css';

function App() {
  return (
    <MantineProvider>
      <Notifications />
      <DatesProvider settings={{ locale: 'es', firstDayOfWeek: 0 }}>
        <UserModeProvider>
          <BrowserRouter>
            <AppShell>
              <AppRoutes />
            </AppShell>
          </BrowserRouter>
        </UserModeProvider>
      </DatesProvider>
    </MantineProvider>
  );
}

export default App;