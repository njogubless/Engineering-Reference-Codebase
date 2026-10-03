import { useState, type SubmitEvent } from 'react';
import { useLocation, useNavigate } from 'react-router';

import { toAppError, type AppError } from '../../lib/errors';
import { ErrorAlert } from '../../shared/ui/ErrorAlert';
import { useAuth } from './AuthProvider';

/** FormData values may be files; these fields are text inputs. */
function fieldValue(form: FormData, name: string): string {
  const value = form.get(name);
  return typeof value === 'string' ? value : '';
}

export function SignInPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<AppError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return; // no double submits
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    setError(null);
    try {
      await signIn(fieldValue(form, 'email'), fieldValue(form, 'password'));
      const from = (location.state as { from?: string } | null)?.from ?? '/';
      await navigate(from, { replace: true });
    } catch (caught) {
      setError(toAppError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main>
      <h1>Sign in</h1>
      <form
        onSubmit={(event) => {
          void handleSubmit(event);
        }}
      >
        <label>
          Email
          <input name="email" type="email" autoComplete="username" required />
        </label>
        <label>
          Password
          <input name="password" type="password" autoComplete="current-password" required />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      {error !== null &&
        (error.code === 'authentication_error' ? (
          <p role="alert">Email or password is incorrect.</p>
        ) : (
          <ErrorAlert error={error} />
        ))}
      <p>Demo account (after `make seed`): ada@example.com / demo-password-123</p>
    </main>
  );
}
