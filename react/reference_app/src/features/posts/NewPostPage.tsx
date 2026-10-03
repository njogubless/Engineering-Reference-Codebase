import { useState, type SubmitEvent } from 'react';
import { useNavigate } from 'react-router';

import { toAppError } from '../../lib/errors';
import { ErrorAlert } from '../../shared/ui/ErrorAlert';
import { useCreatePost } from './api';

/**
 * A deliberately small form. Phase 5 covers forms in depth (react-hook-form,
 * zod, async validation); this one shows the essential part: server field
 * errors land next to the field they belong to.
 */
export function NewPostPage() {
  const create = useCreatePost();
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [publish, setPublish] = useState(false);

  const fieldErrors = create.isError ? toAppError(create.error).fieldErrors : [];
  const errorFor = (field: string) => fieldErrors.find((error) => error.field === field)?.message;
  const titleError = errorFor('title');

  function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    create.mutate(
      { title, body, status: publish ? 'published' : 'draft' },
      { onSuccess: (post) => void navigate(`/posts/${post.id}`) },
    );
  }

  return (
    <main>
      <h1>New post</h1>
      <form onSubmit={handleSubmit} noValidate>
        <label>
          Title
          <input
            value={title}
            onChange={(event) => {
              setTitle(event.target.value);
            }}
            aria-invalid={titleError !== undefined}
            aria-describedby={titleError !== undefined ? 'title-error' : undefined}
          />
        </label>
        {titleError !== undefined && <p id="title-error">{titleError}</p>}
        <label>
          Body
          <textarea
            value={body}
            onChange={(event) => {
              setBody(event.target.value);
            }}
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={publish}
            onChange={(event) => {
              setPublish(event.target.checked);
            }}
          />
          Publish now
        </label>
        <button type="submit" disabled={create.isPending}>
          {create.isPending ? 'Saving…' : 'Save'}
        </button>
      </form>
      {create.isError && fieldErrors.length === 0 && <ErrorAlert error={create.error} />}
    </main>
  );
}
