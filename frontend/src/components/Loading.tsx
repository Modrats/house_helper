import type { ReactNode } from 'react';

interface LoadingProps {
  message?: string;
}

/**
 * Loading spinner component for async states.
 */
export function Loading({ message = 'Loading...' }: LoadingProps): ReactNode {
  return (
    <div className="loading" role="status" aria-live="polite">
      <div className="loading-spinner" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

interface LoadingOverlayProps {
  isLoading: boolean;
  children: ReactNode;
  message?: string;
}

/**
 * Loading overlay that dims content while loading.
 */
export function LoadingOverlay({ 
  isLoading, 
  children, 
  message 
}: LoadingOverlayProps): ReactNode {
  return (
    <div className="loading-overlay-container">
      {children}
      {isLoading && (
        <div className="loading-overlay">
          <Loading message={message} />
        </div>
      )}
    </div>
  );
}
