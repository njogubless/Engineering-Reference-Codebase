import type { Post } from '../features/posts/api';

let counter = 0;

export function makePost(overrides: Partial<Post> = {}): Post {
  counter += 1;
  return {
    id: `01900000-0000-7000-8000-${String(counter).padStart(12, '0')}`,
    title: `Post ${String(counter)}`,
    body: 'Body',
    status: 'published',
    author: { id: '01900000-0000-7000-8000-000000000001', display_name: 'Ada' },
    comment_count: 0,
    created_at: '2026-07-01T16:00:00Z',
    updated_at: '2026-07-01T16:00:00Z',
    published_at: '2026-07-01T16:00:00Z',
    ...overrides,
  };
}

export const problem = (status: number, code: string, extra: Record<string, unknown> = {}) => ({
  type: `https://errors.reference.dev/${code}`,
  title: 'T',
  status,
  code,
  request_id: 'req-1',
  ...extra,
});
