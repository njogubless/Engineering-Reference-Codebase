import { render } from '@testing-library/react';
import type { ReactElement } from 'react';

import { AppProviders } from '../app/providers';
import { createHttpClient } from '../lib/http';
import { API } from './server';

/** Renders with real providers and a fast-failing HTTP client (no retry delays). */
export function renderWithProviders(ui: ReactElement) {
  const http = createHttpClient({ baseUrl: API, sleep: () => Promise.resolve() });
  return render(
    <AppProviders config={{ apiBaseUrl: API, environment: 'test' }} http={http}>
      {ui}
    </AppProviders>,
  );
}
