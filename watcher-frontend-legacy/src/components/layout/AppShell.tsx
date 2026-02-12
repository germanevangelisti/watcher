import { AppShell as MantineAppShell } from '@mantine/core';
import { MainNavbar } from './MainNavbar';
import { MainHeader } from './MainHeader';

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <MantineAppShell
      padding="md"
      navbar={{ width: 300, breakpoint: 'sm' }}
      header={{ height: 60 }}
    >
      <MantineAppShell.Navbar>
        <MainNavbar />
      </MantineAppShell.Navbar>

      <MantineAppShell.Header>
        <MainHeader />
      </MantineAppShell.Header>

      <MantineAppShell.Main>
        {children}
      </MantineAppShell.Main>
    </MantineAppShell>
  );
}