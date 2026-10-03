/**
 * Server state for posts, with TanStack Query.
 *
 * - A query-key factory keeps keys consistent, so invalidation is precise:
 *   `postKeys.lists()` matches every list, `postKeys.detail(id)` one post.
 * - Lists use cursor pagination (`useInfiniteQuery` + `next_cursor`).
 * - Edits are optimistic: the cache changes immediately, rolls back if the
 *   server refuses, and is re-synced from the server either way.
 * - Creating a post is NOT retried by the HTTP client (POST without an
 *   Idempotency-Key), so a timeout cannot create two posts.
 */
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type InfiniteData,
  type QueryClient,
} from '@tanstack/react-query';

import { useServices } from '../../app/providers';
import type { components } from '../../lib/api/schema';

export type Post = components['schemas']['Post'];
export type PostPage = components['schemas']['PostPage'];
export type PostCreate = components['schemas']['PostCreate'];
export type PostUpdate = components['schemas']['PostUpdate'];
export type Comment = components['schemas']['Comment'];
export type CommentPage = components['schemas']['CommentPage'];

const PAGE_SIZE = 10;

export const postKeys = {
  all: ['posts'] as const,
  lists: () => [...postKeys.all, 'list'] as const,
  detail: (id: string) => [...postKeys.all, 'detail', id] as const,
  comments: (id: string) => [...postKeys.all, 'detail', id, 'comments'] as const,
};

export function usePosts() {
  const { http } = useServices();
  return useInfiniteQuery({
    queryKey: postKeys.lists(),
    queryFn: ({ pageParam, signal }) =>
      http.get<PostPage>('/api/v1/posts', { query: { cursor: pageParam, limit: PAGE_SIZE }, signal }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  });
}

export function usePost(postId: string) {
  const { http } = useServices();
  return useQuery({
    queryKey: postKeys.detail(postId),
    queryFn: ({ signal }) => http.get<Post>(`/api/v1/posts/${postId}`, { signal }),
  });
}

export function useComments(postId: string) {
  const { http } = useServices();
  return useInfiniteQuery({
    queryKey: postKeys.comments(postId),
    queryFn: ({ pageParam, signal }) =>
      http.get<CommentPage>(`/api/v1/posts/${postId}/comments`, {
        query: { cursor: pageParam, limit: PAGE_SIZE },
        signal,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  });
}

export function useCreatePost() {
  const { http } = useServices();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PostCreate) => http.post<Post>('/api/v1/posts', data),
    onSuccess: (post) => {
      // Seed the detail cache (the next screen renders instantly) and mark
      // every list stale: where the new post lands depends on the server.
      queryClient.setQueryData(postKeys.detail(post.id), post);
      void queryClient.invalidateQueries({ queryKey: postKeys.lists() });
    },
  });
}

/** Applies `change` to the post wherever it is cached: its detail entry and every list page. */
function patchCachedPost(queryClient: QueryClient, postId: string, change: (post: Post) => Post | null) {
  queryClient.setQueryData<Post>(postKeys.detail(postId), (post) =>
    post ? (change(post) ?? undefined) : post,
  );
  queryClient.setQueriesData<InfiniteData<PostPage>>({ queryKey: postKeys.lists() }, (data) =>
    data
      ? {
          ...data,
          pages: data.pages.map((page) => ({
            ...page,
            items: page.items.flatMap((post) => {
              if (post.id !== postId) return [post];
              const changed = change(post);
              return changed ? [changed] : [];
            }),
          })),
        }
      : data,
  );
}

interface Snapshot {
  detail: Post | undefined;
  lists: [readonly unknown[], InfiniteData<PostPage> | undefined][];
}

async function snapshot(queryClient: QueryClient, postId: string): Promise<Snapshot> {
  // Stop in-flight fetches: a response arriving now would overwrite the
  // optimistic state with stale data.
  await queryClient.cancelQueries({ queryKey: postKeys.all });
  return {
    detail: queryClient.getQueryData<Post>(postKeys.detail(postId)),
    lists: queryClient.getQueriesData<InfiniteData<PostPage>>({ queryKey: postKeys.lists() }),
  };
}

function restore(queryClient: QueryClient, postId: string, saved: Snapshot | undefined) {
  if (saved === undefined) return;
  queryClient.setQueryData(postKeys.detail(postId), saved.detail);
  for (const [key, data] of saved.lists) queryClient.setQueryData(key, data);
}

export function useUpdatePost(postId: string) {
  const { http } = useServices();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (changes: PostUpdate) => http.patch<Post>(`/api/v1/posts/${postId}`, changes),
    onMutate: async (changes) => {
      const saved = await snapshot(queryClient, postId);
      patchCachedPost(queryClient, postId, (post) => ({ ...post, ...changes }));
      return saved;
    },
    onError: (_error, _changes, saved) => {
      restore(queryClient, postId, saved);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: postKeys.all }),
  });
}

export function useDeletePost(postId: string) {
  const { http } = useServices();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => http.delete<undefined>(`/api/v1/posts/${postId}`),
    onMutate: async () => {
      const saved = await snapshot(queryClient, postId);
      patchCachedPost(queryClient, postId, () => null);
      return saved;
    },
    onError: (_error, _variables, saved) => {
      restore(queryClient, postId, saved);
    },
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: postKeys.detail(postId) });
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: postKeys.lists() }),
  });
}

export function useCreateComment(postId: string) {
  const { http } = useServices();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => http.post<Comment>(`/api/v1/posts/${postId}/comments`, { body }),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: postKeys.comments(postId) }),
        queryClient.invalidateQueries({ queryKey: postKeys.detail(postId), exact: true }),
      ]),
  });
}
