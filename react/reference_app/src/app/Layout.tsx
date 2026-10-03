import { Link, NavLink, Outlet } from 'react-router';

import { useAuth } from '../features/auth/AuthProvider';
import { ErrorBoundary } from './ErrorBoundary';

export function Layout() {
  const { user, signOut } = useAuth();
  return (
    <>
      <header>
        <nav aria-label="Main">
          <NavLink to="/" end>
            Posts
          </NavLink>{' '}
          <NavLink to="/diagnostics">Diagnostics</NavLink>{' '}
          {user === null ? (
            <Link to="/sign-in">Sign in</Link>
          ) : (
            <>
              <span>Signed in as {user.display_name}</span>{' '}
              <button
                type="button"
                onClick={() => {
                  void signOut();
                }}
              >
                Sign out
              </button>
            </>
          )}
        </nav>
      </header>
      {/* A render error in one page leaves the navigation usable. */}
      <ErrorBoundary>
        <Outlet />
      </ErrorBoundary>
    </>
  );
}

export function NotFoundPage() {
  return (
    <main>
      <h1>Page not found</h1>
      <Link to="/">Back to posts</Link>
    </main>
  );
}
