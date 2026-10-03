import { useQueryClient } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useMemo, useSyncExternalStore, type ReactNode } from 'react';

import { useServices } from '../../app/providers';
import type { components } from '../../lib/api/schema';
import { logger } from '../../lib/logger';
import type { Session, User } from './session';

type TokenPair = components['schemas']['TokenPair'];

interface AuthContextValue {
  user: User | null;
  // Properties, not methods: components destructure them (`const { signIn } = useAuth()`).
  signIn: (email: string, password: string) => Promise<User>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Auth state and actions in one place. Components call `useAuth()`; they
 * never touch tokens, and the HTTP client reads the token from the store.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const { http, session } = useServices();
  const queryClient = useQueryClient();
  const current = useSyncExternalStore(session.subscribe, session.get);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const tokens = await http.post<TokenPair>('/api/v1/auth/token', { email, password });
      const user = await http.get<User>('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${tokens.access}` },
      });
      const next: Session = { user, ...tokens };
      session.set(next);
      // Cached data may differ per user (e.g. drafts); start from a clean cache.
      queryClient.clear();
      return user;
    },
    [http, session, queryClient],
  );

  const signOut = useCallback(async () => {
    const refresh = session.get()?.refresh;
    session.set(null);
    // Private data must not survive sign-out (shared computers).
    queryClient.clear();
    if (refresh !== undefined) {
      try {
        await http.post('/api/v1/auth/logout', { refresh });
      } catch (error) {
        // Best effort: the local session is already gone, and the refresh
        // token expires on its own. Log it, but never block signing out.
        logger.warn('logout_request_failed', { error });
      }
    }
  }, [http, session, queryClient]);

  const value = useMemo(() => ({ user: current?.user ?? null, signIn, signOut }), [current, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (value === null) throw new Error('useAuth must be used inside <AuthProvider>');
  return value;
}
