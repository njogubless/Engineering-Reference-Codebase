import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';

import { useAuth } from './AuthProvider';

/** Minimal route guard; Phase 4 covers guards, redirects and roles in depth. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  if (user === null) {
    // Remember where the user was going, so sign-in can send them back.
    return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  }
  return children;
}
