import { ConfigError, readConfig } from './config';

describe('readConfig', () => {
  it('reads a valid configuration', () => {
    expect(
      readConfig({ VITE_API_BASE_URL: 'https://api.example.com', VITE_ENVIRONMENT: 'production' }),
    ).toEqual({ apiBaseUrl: 'https://api.example.com', environment: 'production' });
  });

  it('reports every problem at once', () => {
    try {
      readConfig({ VITE_ENVIRONMENT: 'prod' });
      expect.fail('expected ConfigError');
    } catch (error) {
      expect(error).toBeInstanceOf(ConfigError);
      expect((error as ConfigError).problems).toEqual([
        'VITE_API_BASE_URL is required',
        'VITE_ENVIRONMENT must be one of development, test, staging, production',
      ]);
    }
  });

  it.each([
    [{ VITE_API_BASE_URL: 'not a url', VITE_ENVIRONMENT: 'test' }, 'must be an absolute URL'],
    [{ VITE_API_BASE_URL: 'ftp://x', VITE_ENVIRONMENT: 'test' }, 'must be http(s)'],
    [{ VITE_API_BASE_URL: 'http://api.example.com', VITE_ENVIRONMENT: 'production' }, 'must use https'],
  ])('rejects %j', (env, message) => {
    expect(() => readConfig(env)).toThrow(message);
  });
});
