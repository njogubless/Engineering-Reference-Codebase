import { useQueryClient } from '@tanstack/react-query';
import { act, renderHook, screen, waitFor, within } from '@testing-library/react';
import type { ReactNode } from 'react';
import userEvent from '@testing-library/user-event';
import { delay, http as mock, HttpResponse } from 'msw';

import { makePost, problem } from '../../test/fixtures';
import { ADA, renderRoute, TestProviders } from '../../test/render';
import { useDeletePost, usePosts } from './api';

function providers({ children }: { children: ReactNode }) {
  return <TestProviders session={ADA}>{children}</TestProviders>;
}
import { API, server } from '../../test/server';

describe('list', () => {
  it('pages through posts with the cursor and shows the end', async () => {
    const first = [makePost({ title: 'First' })];
    const second = [makePost({ title: 'Second' })];
    server.use(
      mock.get(`${API}/api/v1/posts`, ({ request }) => {
        const cursor = new URL(request.url).searchParams.get('cursor');
        return HttpResponse.json(
          cursor === 'c1' ? { items: second, next_cursor: null } : { items: first, next_cursor: 'c1' },
        );
      }),
    );
    renderRoute('/');
    expect(await screen.findByText('First')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Load more' }));
    expect(await screen.findByText('Second')).toBeInTheDocument();
    expect(screen.getByText('You have reached the end.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Load more' })).not.toBeInTheDocument();
  });

  it('shows an empty state', async () => {
    server.use(mock.get(`${API}/api/v1/posts`, () => HttpResponse.json({ items: [], next_cursor: null })));
    renderRoute('/');
    expect(await screen.findByText('No posts yet.')).toBeInTheDocument();
  });
});

describe('optimistic updates', () => {
  const draft = makePost({ status: 'draft', published_at: null, title: 'My draft' });

  function serveDraft() {
    server.use(mock.get(`${API}/api/v1/posts/${draft.id}`, () => HttpResponse.json(draft)));
  }

  it('shows the change immediately, before the server answers', async () => {
    serveDraft();
    server.use(
      mock.patch(`${API}/api/v1/posts/${draft.id}`, async () => {
        await delay(100);
        return HttpResponse.json({ ...draft, status: 'published', published_at: '2026-07-02T10:00:00Z' });
      }),
    );
    renderRoute(`/posts/${draft.id}`, { session: ADA });
    await userEvent.click(await screen.findByRole('button', { name: 'Publish' }));
    // Optimistic: flipped before the delayed response arrives.
    expect(screen.getByRole('button', { name: 'Unpublish' })).toBeInTheDocument();
  });

  it('rolls back and explains when the server refuses', async () => {
    serveDraft();
    server.use(
      mock.patch(`${API}/api/v1/posts/${draft.id}`, () =>
        HttpResponse.json(problem(403, 'authorization_error'), { status: 403 }),
      ),
    );
    renderRoute(`/posts/${draft.id}`, { session: ADA });
    await userEvent.click(await screen.findByRole('button', { name: 'Publish' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('You do not have permission');
    expect(screen.getByRole('button', { name: 'Publish' })).toBeInTheDocument();
  });

  it('removes a deleted post from cached lists before the server confirms, and restores it on failure', async () => {
    const keep = makePost({ title: 'Keep' });
    const doomed = makePost({ title: 'Doomed' });
    let release: (ok: boolean) => void = () => undefined;
    server.use(
      mock.get(`${API}/api/v1/posts`, () => HttpResponse.json({ items: [keep, doomed], next_cursor: null })),
      mock.delete(
        `${API}/api/v1/posts/${doomed.id}`,
        () =>
          new Promise<Response>((resolve) => {
            release = (ok) => {
              resolve(
                ok
                  ? new HttpResponse(null, { status: 204 })
                  : // Not 503: DELETE is idempotent, so the client would retry it.
                    HttpResponse.json(problem(403, 'authorization_error'), { status: 403 }),
              );
            };
          }),
      ),
    );
    const { result } = renderHook(
      () => ({ list: usePosts(), remove: useDeletePost(doomed.id), client: useQueryClient() }),
      { wrapper: providers },
    );
    await waitFor(() => {
      expect(result.current.list.isSuccess).toBe(true);
    });
    const titles = () => result.current.list.data?.pages.flatMap((page) => page.items.map((p) => p.title));

    act(() => {
      result.current.remove.mutate();
    });
    await waitFor(() => {
      expect(titles()).toEqual(['Keep']); // optimistic: server has not answered yet
    });

    act(() => {
      release(false);
    });
    await waitFor(() => {
      expect(result.current.remove.isError).toBe(true);
    });
    expect(titles()).toEqual(['Keep', 'Doomed']); // rolled back
  });
});

describe('creating', () => {
  it('redirects anonymous users to sign-in', async () => {
    const { router } = renderRoute('/posts/new');
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/sign-in');
    });
  });

  it('shows server field errors next to the field and sends the token', async () => {
    let authorization: string | null = null;
    server.use(
      mock.post(`${API}/api/v1/posts`, ({ request }) => {
        authorization = request.headers.get('authorization');
        return HttpResponse.json(
          problem(422, 'validation_error', {
            errors: [{ field: 'title', code: 'blank', message: 'This field may not be blank.' }],
          }),
          { status: 422 },
        );
      }),
    );
    renderRoute('/posts/new', { session: ADA });
    await userEvent.click(await screen.findByRole('button', { name: 'Save' }));
    expect(await screen.findByText('This field may not be blank.')).toBeInTheDocument();
    expect(screen.getByLabelText('Title')).toHaveAttribute('aria-invalid', 'true');
    expect(authorization).toBe('Bearer access-token');
  });

  it('navigates to the created post, rendered from the seeded cache', async () => {
    const created = makePost({ title: 'Brand new', status: 'draft', published_at: null });
    server.use(mock.post(`${API}/api/v1/posts`, () => HttpResponse.json(created, { status: 201 })));
    // The detail screen renders from the seeded cache; this serves its background refetch.
    server.use(mock.get(`${API}/api/v1/posts/${created.id}`, () => HttpResponse.json(created)));
    renderRoute('/posts/new', { session: ADA });
    await userEvent.type(await screen.findByLabelText('Title'), 'Brand new');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByRole('heading', { name: 'Brand new' })).toBeInTheDocument();
  });
});

describe('comments', () => {
  it('lists comments and adds one', async () => {
    const post = makePost({ comment_count: 1 });
    const comments = [
      {
        id: 'c1',
        post_id: post.id,
        body: 'Nice',
        author: { id: 'u2', display_name: 'Grace' },
        created_at: post.created_at,
      },
    ];
    server.use(
      mock.get(`${API}/api/v1/posts/${post.id}`, () => HttpResponse.json(post)),
      mock.get(`${API}/api/v1/posts/${post.id}/comments`, () =>
        HttpResponse.json({ items: comments, next_cursor: null }),
      ),
      mock.post(`${API}/api/v1/posts/${post.id}/comments`, async ({ request }) => {
        const { body } = (await request.json()) as { body: string };
        const comment = { ...comments[0]!, id: 'c2', body };
        comments.push(comment);
        return HttpResponse.json(comment, { status: 201 });
      }),
    );
    renderRoute(`/posts/${post.id}`, { session: ADA });
    const list = await screen.findByRole('list', { name: 'Comments' });
    expect(within(list).getByText('Nice')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Add a comment'), 'Great post');
    await userEvent.click(screen.getByRole('button', { name: 'Comment' }));
    expect(await within(list).findByText('Great post')).toBeInTheDocument();
  });
});
