import { useState } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';

import { routes } from './routes';

export function App() {
  const [router] = useState(() => createBrowserRouter(routes));
  return <RouterProvider router={router} />;
}
