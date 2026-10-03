import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http as mock, HttpResponse } from 'msw';

import { makePost, problem } from '../../test/fixtures';
import { ADA, renderRoute } from '../../test/render';
import { API, server } from '../../test/server';

function serveSignIn() {
  server.use(
    mock.post(`${API}/api/v1/auth/token`, async ({ request }) => {
      const { password } = (await request.json()) as { password: string };
      return password === 'right-password'
        ? HttpResponse.json({ access: 'new-access', refresh: 'new-refresh' })
        : HttpResponse.json(problem(401, 'authentication_error'), { status: 401 });
    }),
    mock.get(`${API}/api/v1/auth/me`, () => HttpResponse.json(ADA.user)),
    mock.get(`${API}/api/v1/posts`, () => HttpResponse.json({ items: [], next_cursor: null })),
  );
}

async function signIn(password: string) {
  await userEvent.type(await screen.findByLabelText('Email'), 'ada@example.com');
  await userEvent.type(screen.getByLabelText('Password'), password);
  await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
}

it('signs in and returns to the page that required it', async () => {
  serveSignIn();
  const { router, session } = renderRoute('/posts/new');
  await signIn('right-password');
  await waitFor(() => {
    expect(router.state.location.pathname).toBe('/posts/new');
  });
  expect(session.get()?.access).toBe('new-access');
  expect(screen.getByText('Signed in as Ada')).toBeInTheDocument();
});

it('shows one message for wrong credentials', async () => {
  serveSignIn();
  renderRoute('/sign-in');
  await signIn('wrong-password');
  expect(await screen.findByRole('alert')).toHaveTextContent('Email or password is incorrect.');
});

it('signing out revokes the refresh token and drops cached private data', async () => {
  let revoked: unknown = null;
  const draft = makePost({ status: 'draft', published_at: null, title: 'Private draft' });
  server.use(
    mock.get(`${API}/api/v1/posts`, () => HttpResponse.json({ items: [], next_cursor: null })),
    mock.get(`${API}/api/v1/posts/${draft.id}`, () => HttpResponse.json(draft)),
    mock.post(`${API}/api/v1/auth/logout`, async ({ request }) => {
      revoked = await request.json();
      return new HttpResponse(null, { status: 204 });
    }),
  );
  const { router, session } = renderRoute(`/posts/${draft.id}`, { session: ADA });
  expect(await screen.findByText('Private draft')).toBeInTheDocument();

  await userEvent.click(screen.getByRole('button', { name: 'Sign out' }));
  expect(session.get()).toBeNull();
  await waitFor(() => {
    expect(revoked).toEqual({ refresh: 'refresh-token' });
  });
  await router.navigate('/');
  expect(screen.getByRole('link', { name: 'Sign in' })).toBeInTheDocument();
});

it('a 401 on an authenticated request ends the session', async () => {
  server.use(
    mock.get(`${API}/api/v1/posts`, () =>
      HttpResponse.json(problem(401, 'authentication_error'), { status: 401 }),
    ),
  );
  const { session } = renderRoute('/', { session: ADA });
  await waitFor(() => {
    expect(session.get()).toBeNull();
  });
});
