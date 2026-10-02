import { useState } from 'react';

import { useServices } from '../../app/providers';
import { ErrorAlert } from '../../shared/ui/ErrorAlert';
import { useMeta, useMissingResource, useReadiness } from './api';

/**
 * Phase 1 demo: configuration, health checks, feature flags and the error
 * model, end to end against whichever backend VITE_API_BASE_URL points at.
 */
export function DiagnosticsPage() {
  const { config } = useServices();
  const meta = useMeta();
  const readiness = useReadiness();
  const [showErrorDemo, setShowErrorDemo] = useState(false);
  const missing = useMissingResource(showErrorDemo);

  return (
    <main>
      <h1>Diagnostics</h1>

      <section aria-labelledby="config-heading">
        <h2 id="config-heading">Client configuration</h2>
        <dl>
          <dt>Environment</dt>
          <dd>{config.environment}</dd>
          <dt>API base URL</dt>
          <dd>{config.apiBaseUrl}</dd>
        </dl>
      </section>

      <section aria-labelledby="server-heading">
        <h2 id="server-heading">Server</h2>
        {meta.isPending && <p>Loading server configuration…</p>}
        {meta.isError && (
          <ErrorAlert
            error={meta.error}
            onRetry={() => {
              void meta.refetch();
            }}
          />
        )}
        {meta.isSuccess && (
          <dl>
            <dt>Server environment</dt>
            <dd>{meta.data.environment}</dd>
            <dt>API version</dt>
            <dd>{meta.data.api_version}</dd>
            <dt>Feature flags</dt>
            <dd>
              {Object.keys(meta.data.features).length === 0 ? (
                'None'
              ) : (
                <ul>
                  {Object.entries(meta.data.features).map(([name, enabled]) => (
                    <li key={name}>
                      {name}: {enabled ? 'on' : 'off'}
                    </li>
                  ))}
                </ul>
              )}
            </dd>
          </dl>
        )}
      </section>

      <section aria-labelledby="health-heading">
        <h2 id="health-heading">Readiness</h2>
        {readiness.isPending && <p>Checking dependencies…</p>}
        {readiness.isError && <ErrorAlert error={readiness.error} />}
        {readiness.isSuccess && (
          <ul>
            {Object.entries(readiness.data.checks).map(([name, result]) => (
              <li key={name}>
                {name}: {result}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="errors-heading">
        <h2 id="errors-heading">Error handling demo</h2>
        <button
          type="button"
          onClick={() => {
            setShowErrorDemo(true);
          }}
        >
          Request a missing resource
        </button>
        {missing.isError && <ErrorAlert error={missing.error} />}
      </section>
    </main>
  );
}
