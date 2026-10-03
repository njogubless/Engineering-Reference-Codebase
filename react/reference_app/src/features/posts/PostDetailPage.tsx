import { useState, type SubmitEvent } from 'react';
import { useNavigate, useParams } from 'react-router';

import { formatDateTime } from '../../lib/time';
import { ErrorAlert } from '../../shared/ui/ErrorAlert';
import { useAuth } from '../auth/AuthProvider';
import { useComments, useCreateComment, useDeletePost, usePost, useUpdatePost, type Post } from './api';

export function PostDetailPage() {
  const { postId = '' } = useParams();
  const post = usePost(postId);

  if (post.isPending) return <p>Loading post…</p>;
  if (post.isError) return <ErrorAlert error={post.error} />;
  return <PostView post={post.data} />;
}

function PostView({ post }: { post: Post }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const update = useUpdatePost(post.id);
  const remove = useDeletePost(post.id);
  const isAuthor = user?.id === post.author.id;

  return (
    <main>
      <h1>{post.title}</h1>
      <p>
        by {post.author.display_name} · {post.status}
        {post.published_at !== null && <> · {formatDateTime(post.published_at)}</>}
      </p>
      <p>{post.body}</p>

      {isAuthor && (
        <div>
          <button
            type="button"
            disabled={update.isPending}
            onClick={() => {
              update.mutate({ status: post.status === 'published' ? 'draft' : 'published' });
            }}
          >
            {post.status === 'published' ? 'Unpublish' : 'Publish'}
          </button>
          <button
            type="button"
            disabled={remove.isPending}
            onClick={() => {
              remove.mutate(undefined, { onSuccess: () => void navigate('/') });
            }}
          >
            Delete
          </button>
        </div>
      )}
      {update.isError && <ErrorAlert error={update.error} />}
      {remove.isError && <ErrorAlert error={remove.error} />}

      {post.status === 'published' && <Comments postId={post.id} />}
    </main>
  );
}

function Comments({ postId }: { postId: string }) {
  const { user } = useAuth();
  const comments = useComments(postId);
  const create = useCreateComment(postId);
  const [body, setBody] = useState('');

  function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    create.mutate(body, {
      onSuccess: () => {
        setBody('');
      },
    });
  }

  return (
    <section aria-labelledby="comments-heading">
      <h2 id="comments-heading">Comments</h2>
      {comments.isError && <ErrorAlert error={comments.error} />}
      {comments.isSuccess && (
        <ul aria-label="Comments">
          {comments.data.pages.flatMap((page) =>
            page.items.map((comment) => (
              <li key={comment.id}>
                {comment.body} <small>— {comment.author.display_name}</small>
              </li>
            )),
          )}
        </ul>
      )}
      {comments.hasNextPage && (
        <button
          type="button"
          onClick={() => {
            void comments.fetchNextPage();
          }}
        >
          More comments
        </button>
      )}
      {user !== null && (
        <form onSubmit={handleSubmit}>
          <label>
            Add a comment
            <textarea
              value={body}
              onChange={(event) => {
                setBody(event.target.value);
              }}
              required
            />
          </label>
          <button type="submit" disabled={create.isPending}>
            Comment
          </button>
          {create.isError && <ErrorAlert error={create.error} />}
        </form>
      )}
    </section>
  );
}
