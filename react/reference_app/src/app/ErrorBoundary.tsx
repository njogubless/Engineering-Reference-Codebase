import { Component, type ErrorInfo, type ReactNode } from 'react';

import { logger } from '../lib/logger';

interface Props {
  children: ReactNode;
  fallback?: (reset: () => void) => ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * Catches errors thrown while *rendering*. It does not catch errors in event
 * handlers or async code — those are handled where they occur (and surface
 * through TanStack Query's `error` state).
 *
 * Error boundaries must still be class components; there is no hook equivalent.
 */
export class ErrorBoundary extends Component<Props, State> {
  override state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    logger.error('render_error', { message: error.message, componentStack: info.componentStack });
  }

  reset = (): void => {
    this.setState({ hasError: false });
  };

  override render(): ReactNode {
    if (!this.state.hasError) return this.props.children;
    if (this.props.fallback) return this.props.fallback(this.reset);
    return (
      <div role="alert">
        <h2>Something went wrong.</h2>
        <p>The problem has been logged. You can try again.</p>
        <button type="button" onClick={this.reset}>
          Try again
        </button>
      </div>
    );
  }
}
