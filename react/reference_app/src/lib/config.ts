/**
 * Typed, validated runtime configuration.
 *
 * Vite inlines `VITE_*` variables into the JavaScript bundle at build time,
 * so they are PUBLIC: anyone can read them in the browser. API URLs and
 * public keys belong here; secrets never do — secrets live on the server.
 *
 * Validation happens once at startup; a misconfigured build shows a clear
 * error screen instead of failing on the first API call.
 */
export const ENVIRONMENTS = ['development', 'test', 'staging', 'production'] as const;
export type Environment = (typeof ENVIRONMENTS)[number];

export interface AppConfig {
  apiBaseUrl: string;
  environment: Environment;
}

export class ConfigError extends Error {
  override readonly name = 'ConfigError';
  readonly problems: string[];

  constructor(problems: string[]) {
    super(`Invalid configuration: ${problems.join('; ')}`);
    this.problems = problems;
  }
}

function isEnvironment(value: string): value is Environment {
  return (ENVIRONMENTS as readonly string[]).includes(value);
}

export function readConfig(env: Record<string, string | boolean | undefined>): AppConfig {
  const problems: string[] = [];

  const rawUrl = env.VITE_API_BASE_URL;
  let apiBaseUrl = '';
  if (typeof rawUrl !== 'string' || rawUrl === '') {
    problems.push('VITE_API_BASE_URL is required');
  } else {
    try {
      const url = new URL(rawUrl);
      if (url.protocol !== 'http:' && url.protocol !== 'https:')
        problems.push('VITE_API_BASE_URL must be http(s)');
      apiBaseUrl = rawUrl;
    } catch {
      problems.push('VITE_API_BASE_URL must be an absolute URL');
    }
  }

  const rawEnvironment = env.VITE_ENVIRONMENT;
  let environment: Environment = 'development';
  if (typeof rawEnvironment !== 'string' || !isEnvironment(rawEnvironment)) {
    problems.push(`VITE_ENVIRONMENT must be one of ${ENVIRONMENTS.join(', ')}`);
  } else {
    environment = rawEnvironment;
  }

  if (environment === 'production' && apiBaseUrl.startsWith('http:')) {
    problems.push('VITE_API_BASE_URL must use https in production');
  }

  if (problems.length > 0) throw new ConfigError(problems);
  return { apiBaseUrl, environment };
}
