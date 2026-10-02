import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './app/App';
import { AppProviders } from './app/providers';
import { ConfigError, readConfig, type AppConfig } from './lib/config';
import { logger } from './lib/logger';
import './styles.css';

const container = document.getElementById('root');
if (container === null) throw new Error('Missing #root element');

const root = createRoot(container, {
  // Global capture for errors React reports (render errors, caught or not).
  onUncaughtError: (error) => {
    logger.error('uncaught_render_error', { error });
  },
  onCaughtError: (error) => {
    logger.warn('caught_render_error', { error });
  },
});

let config: AppConfig | null = null;
try {
  config = readConfig(import.meta.env);
} catch (error) {
  if (!(error instanceof ConfigError)) throw error;
  logger.error('invalid_config', { problems: error.problems });
  root.render(
    <main role="alert">
      <h1>Configuration error</h1>
      <ul>
        {error.problems.map((problem) => (
          <li key={problem}>{problem}</li>
        ))}
      </ul>
    </main>,
  );
}

// Errors outside React (async code nobody awaited) would otherwise vanish.
window.addEventListener('unhandledrejection', (event) => {
  logger.error('unhandled_rejection', { reason: event.reason });
});

if (config !== null) {
  root.render(
    <StrictMode>
      <AppProviders config={config}>
        <App />
      </AppProviders>
    </StrictMode>,
  );
}
