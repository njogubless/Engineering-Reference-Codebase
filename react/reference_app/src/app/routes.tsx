import type { RouteObject } from 'react-router';

import { RequireAuth } from '../features/auth/RequireAuth';
import { SignInPage } from '../features/auth/SignInPage';
import { DiagnosticsPage } from '../features/diagnostics/DiagnosticsPage';
import { NewPostPage } from '../features/posts/NewPostPage';
import { PostDetailPage } from '../features/posts/PostDetailPage';
import { PostsPage } from '../features/posts/PostsPage';
import { Layout, NotFoundPage } from './Layout';

/** One route table for the app (browser router) and tests (memory router). Phase 4 adds lazy routes and guards in depth. */
export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { index: true, element: <PostsPage /> },
      {
        path: 'posts/new',
        element: (
          <RequireAuth>
            <NewPostPage />
          </RequireAuth>
        ),
      },
      { path: 'posts/:postId', element: <PostDetailPage /> },
      { path: 'diagnostics', element: <DiagnosticsPage /> },
      { path: 'sign-in', element: <SignInPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
];
