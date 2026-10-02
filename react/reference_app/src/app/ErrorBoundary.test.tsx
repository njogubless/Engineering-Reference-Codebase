import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ErrorBoundary } from './ErrorBoundary';

let shouldThrow = true;

function Bomb() {
  if (shouldThrow) throw new Error('render failed');
  return <p>Recovered</p>;
}

it('renders a fallback for render errors and can reset', async () => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined);
  render(
    <ErrorBoundary>
      <Bomb />
    </ErrorBoundary>,
  );
  expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong.');

  shouldThrow = false;
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
  expect(screen.getByText('Recovered')).toBeInTheDocument();
});
