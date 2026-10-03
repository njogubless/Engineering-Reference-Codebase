import { render } from '@testing-library/react';
import { useState, type ReactElement, type ReactNode } from 'react';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { AppProviders } from '../app/providers';
import { routes } from '../app/routes';
import { createSessionStore, type Session } from '../features/auth/session';
import { API } from './server';

const config = { apiBaseUrl: API, environment: 'test' as const };
const fastHttp = { sleep: () => Promise.resolve() };

/** Renders with real providers and a fast-failing HTTP client (no retry delays). */
export function renderWithProviders(ui: ReactElement, { session }: { session?: Session } = {}) {
  return render(
    <AppProviders config={config} httpOptions={fastHttp} session={createSessionStore(session ?? null)}>
      {ui}
    </AppProviders>,
  );
}

/** Providers only, for hook tests (`renderHook(..., { wrapper })`). */
export function TestProviders({ children, session }: { children: ReactNode; session?: Session }) {
  const [store] = useState(() => createSessionStore(session ?? null));
  return (
    <AppProviders config={config} httpOptions={fastHttp} session={store}>
      {children}
    </AppProviders>
  );
}

/** Renders the real route table at `path`, as the app would. */
export function renderRoute(path: string, { session }: { session?: Session } = {}) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const store = createSessionStore(session ?? null);
  const view = render(
    <AppProviders config={config} httpOptions={fastHttp} session={store}>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return { ...view, router, session: store };
}

export const ADA: Session = {
  user: {
    id: '01900000-0000-7000-8000-000000000001',
    email: 'ada@example.com',
    display_name: 'Ada',
    date_joined: '2026-01-01T00:00:00Z',
  },
  access: 'access-token',
  refresh: 'refresh-token',
};
