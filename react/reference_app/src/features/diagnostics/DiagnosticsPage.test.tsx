import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http as mock, HttpResponse } from 'msw';

import { API, server } from '../../test/server';
import { renderWithProviders } from '../../test/render';
import { DiagnosticsPage } from './DiagnosticsPage';

function serverUp() {
  server.use(
    mock.get(`${API}/api/v1/meta`, () =>
      HttpResponse.json({ api_version: '1', environment: 'test', features: { maintenance_banner: true } }),
    ),
    mock.get(`${API}/health/ready`, () => HttpResponse.json({ status: 'ok', checks: { database: 'ok' } })),
  );
}

it('shows server configuration and readiness', async () => {
  serverUp();
  renderWithProviders(<DiagnosticsPage />);
  expect(await screen.findByText('maintenance_banner: on')).toBeInTheDocument();
  expect(await screen.findByText('database: ok')).toBeInTheDocument();
});

it('shows a user-facing error with the request reference, and recovers on retry', async () => {
  let fail = true;
  server.use(
    mock.get(`${API}/api/v1/meta`, () =>
      fail
        ? HttpResponse.json(
            {
              type: 't',
              title: 'Internal server error',
              status: 500,
              code: 'internal_error',
              request_id: 'req-42',
            },
            { status: 500 },
          )
        : HttpResponse.json({ api_version: '1', environment: 'test', features: {} }),
    ),
    mock.get(`${API}/health/ready`, () => HttpResponse.json({ status: 'ok', checks: {} })),
  );
  renderWithProviders(<DiagnosticsPage />);

  const alert = await screen.findByRole('alert');
  expect(alert).toHaveTextContent('Something went wrong on our side');
  expect(alert).toHaveTextContent('req-42');

  fail = false;
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
  expect(await screen.findByText('None')).toBeInTheDocument();
});

it('demonstrates a 404 Problem end to end', async () => {
  serverUp();
  server.use(
    mock.get(`${API}/api/v1/does-not-exist`, () =>
      HttpResponse.json(
        { type: 't', title: 'Not found', status: 404, code: 'not_found', request_id: 'req-404' },
        { status: 404 },
      ),
    ),
  );
  renderWithProviders(<DiagnosticsPage />);
  await userEvent.click(screen.getByRole('button', { name: 'Request a missing resource' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('We could not find what you were looking for');
});
