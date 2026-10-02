import { setupServer } from 'msw/node';

/** Mock Service Worker intercepts real `fetch` calls: the code under test is unchanged. */
export const server = setupServer();

export const API = 'http://api.test';
