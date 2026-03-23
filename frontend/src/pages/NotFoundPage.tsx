import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

/**
 * 404 Not Found page for unmatched routes.
 */
export function NotFoundPage(): ReactNode {
  return (
    <div className="page page--not-found">
      <h2>Page Not Found</h2>
      <p>The page you're looking for doesn't exist.</p>
      <Link to="/">Go back to browsing houses</Link>
    </div>
  );
}
