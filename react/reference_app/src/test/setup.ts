import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';

import { server } from './server';

// Unhandled requests fail the test: every network call in a test is explicit.
beforeAll(() => {
  server.listen({ onUnhandledFrame: 'error' });
});
afterEach(() => {
  server.resetHandlers();
  cleanup();
});
afterAll(() => {
  server.close();
});
