import { redact } from './logger';

it('redacts sensitive keys recursively', () => {
  expect(redact({ user: 'a', accessToken: 't', nested: [{ password: 'p' }] })).toEqual({
    user: 'a',
    accessToken: '[REDACTED]',
    nested: [{ password: '[REDACTED]' }],
  });
});
