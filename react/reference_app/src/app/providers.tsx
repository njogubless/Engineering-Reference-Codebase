import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createContext, useContext, useState, type ReactNode } from 'react';

import type { AppConfig } from '../lib/config';
import { createHttpClient, type HttpClient } from '../lib/http';

interface Services {
  config: AppConfig;
  http: HttpClient;
}

const ServicesContext = createContext<Services | null>(null);

/**
 * Dependency injection, React-style: long-lived services are created once and
 * provided through context. Components never import a configured singleton,
 * so tests can render them with a different client.
 */
export function AppProviders({
  config,
  http,
  children,
}: {
  config: AppConfig;
  http?: HttpClient;
  children: ReactNode;
}) {
  const [services] = useState<Services>(() => ({
    config,
    http: http ?? createHttpClient({ baseUrl: config.apiBaseUrl }),
  }));
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
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </ServicesContext.Provider>
  );
}

export function useServices(): Services {
  const services = useContext(ServicesContext);
  if (services === null) throw new Error('useServices must be used inside <AppProviders>');
  return services;
}
