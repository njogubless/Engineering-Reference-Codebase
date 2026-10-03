import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createContext, useContext, useState, type ReactNode } from 'react';

import { AuthProvider } from '../features/auth/AuthProvider';
import { createSessionStore, type SessionStore } from '../features/auth/session';
import type { AppConfig } from '../lib/config';
import { createHttpClient, type HttpClient, type HttpClientConfig } from '../lib/http';

interface Services {
  config: AppConfig;
  http: HttpClient;
  session: SessionStore;
}

const ServicesContext = createContext<Services | null>(null);

/**
 * Dependency injection, React-style: long-lived services are created once and
 * provided through context. Components never import a configured singleton,
 * so tests can render them with a different client.
 */
export function AppProviders({
  config,
  httpOptions,
  session,
  children,
}: {
  config: AppConfig;
  /** Test hooks (fake timers/random); production uses the defaults. */
  httpOptions?: Partial<HttpClientConfig>;
  session?: SessionStore;
  children: ReactNode;
}) {
  const [services] = useState<Services>(() => {
    const store = session ?? createSessionStore();
    return {
      config,
      session: store,
      http: createHttpClient({
        baseUrl: config.apiBaseUrl,
        getAccessToken: () => store.get()?.access ?? null,
        // An expired or revoked access token ends the session (Phase 3: refresh instead).
        onUnauthorized: () => {
          store.set(null);
        },
        ...httpOptions,
      }),
    };
  });
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          // Retry in exactly one layer. The HTTP client already retries
          // transient failures for idempotent requests; letting TanStack Query
          // retry as well would multiply attempts (3 × 3 = 9) — a retry storm.
          queries: { retry: false },
          mutations: { retry: false },
        },
      }),
  );

  return (
    <ServicesContext.Provider value={services}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientProvider>
    </ServicesContext.Provider>
  );
}

export function useServices(): Services {
  const services = useContext(ServicesContext);
  if (services === null) throw new Error('useServices must be used inside <AppProviders>');
  return services;
}
