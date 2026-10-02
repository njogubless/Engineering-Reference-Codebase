import { DiagnosticsPage } from '../features/diagnostics/DiagnosticsPage';
import { ErrorBoundary } from './ErrorBoundary';

export function App() {
  return (
    <ErrorBoundary>
      <DiagnosticsPage />
    </ErrorBoundary>
  );
}
