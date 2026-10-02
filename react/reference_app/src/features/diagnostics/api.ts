/**
 * Typed API calls + TanStack Query hooks for the diagnostics feature.
 * Types come from contracts/openapi.yaml (generated into src/lib/api/schema.d.ts).
 */
import { useQuery } from '@tanstack/react-query';

import { useServices } from '../../app/providers';
import type { components } from '../../lib/api/schema';

export type Meta = components['schemas']['Meta'];
export type Readiness = components['schemas']['Readiness'];

export const diagnosticsKeys = {
  meta: ['diagnostics', 'meta'] as const,
  readiness: ['diagnostics', 'readiness'] as const,
  missing: ['diagnostics', 'missing'] as const,
};

export function useMeta() {
  const { http } = useServices();
  return useQuery({
    queryKey: diagnosticsKeys.meta,
    queryFn: ({ signal }) => http.get<Meta>('/api/v1/meta', { signal }),
  });
}

export function useReadiness() {
  const { http } = useServices();
  return useQuery({
    queryKey: diagnosticsKeys.readiness,
    // A probe reports the current state; retrying would hide it.
    queryFn: ({ signal }) => http.get<Readiness>('/health/ready', { signal, retries: 0 }),
  });
}

/** Deliberately requests a path that does not exist, to show error handling end to end. */
export function useMissingResource(enabled: boolean) {
  const { http } = useServices();
  return useQuery({
    queryKey: diagnosticsKeys.missing,
    queryFn: ({ signal }) => http.get<never>('/api/v1/does-not-exist', { signal }),
    enabled,
  });
}
