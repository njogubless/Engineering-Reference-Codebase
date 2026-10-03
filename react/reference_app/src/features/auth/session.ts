/**
 * The current session, held in memory.
 *
 * Phase 2b keeps sessions deliberately minimal: tokens live only in memory,
 * so a page reload (or the 15-minute access-token expiry) means signing in
 * again. Phase 3 adds the full architecture: refresh-token rotation with a
 * single-flight refresh, session restoration, and the cookie-vs-memory
 * storage decision. Never put tokens in localStorage: any XSS can read it.
 */
import type { components } from '../../lib/api/schema';

export type User = components['schemas']['User'];

export interface Session {
  user: User;
  access: string;
  refresh: string;
}

type Listener = () => void;

/** A tiny observable store, readable outside React (by the HTTP client) and inside it. */
// Function-valued properties (not methods), so they can be passed around
// unbound, e.g. `useSyncExternalStore(store.subscribe, store.get)`.
export interface SessionStore {
  get: () => Session | null;
  set: (session: Session | null) => void;
  subscribe: (listener: Listener) => () => void;
}

export function createSessionStore(initial: Session | null = null): SessionStore {
  let session = initial;
  const listeners = new Set<Listener>();
  return {
    get: () => session,
    set: (next) => {
      session = next;
      listeners.forEach((listener) => {
        listener();
      });
    },
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
