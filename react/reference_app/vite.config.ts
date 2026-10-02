import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    // Tests must not depend on the developer's .env files.
    env: { VITE_API_BASE_URL: 'http://api.test', VITE_ENVIRONMENT: 'test' },
  },
});
