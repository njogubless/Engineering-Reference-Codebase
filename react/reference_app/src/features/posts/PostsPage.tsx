import { Link } from 'react-router';

import { formatDateTime } from '../../lib/time';
import { ErrorAlert } from '../../shared/ui/ErrorAlert';
import { useAuth } from '../auth/AuthProvider';
import { usePosts } from './api';

/** Every async state is handled explicitly: loading, error, empty, data, loading more, end. */
export function PostsPage() {
  const { user } = useAuth();
  const posts = usePosts();

  return (
    <main>
      <h1>Posts</h1>
      {user !== null && <Link to="/posts/new">New post</Link>}

      {posts.isPending && <p>Loading posts…</p>}
      {posts.isError && (
        <ErrorAlert
          error={posts.error}
          onRetry={() => {
            void posts.refetch();
          }}
        />
      )}
      {posts.isSuccess && posts.data.pages[0]?.items.length === 0 && <p>No posts yet.</p>}
      {posts.isSuccess && (
        <ul aria-label="Posts">
          {posts.data.pages.flatMap((page) =>
            page.items.map((post) => (
              <li key={post.id}>
                <Link to={`/posts/${post.id}`}>{post.title}</Link>{' '}
                <small>
                  by {post.author.display_name}
                  {post.published_at !== null && <> · {formatDateTime(post.published_at)}</>} ·{' '}
                  {post.comment_count} {post.comment_count === 1 ? 'comment' : 'comments'}
                </small>
              </li>
            )),
          )}
        </ul>
      )}
      {posts.hasNextPage && (
        <button
          type="button"
          disabled={posts.isFetchingNextPage}
          onClick={() => {
            void posts.fetchNextPage();
          }}
        >
          {posts.isFetchingNextPage ? 'Loading…' : 'Load more'}
        </button>
      )}
      {posts.isSuccess && !posts.hasNextPage && posts.data.pages[0]?.items.length !== 0 && (
        <p>You have reached the end.</p>
      )}
    </main>
  );
}
