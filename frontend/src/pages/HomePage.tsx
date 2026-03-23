import type { ReactNode } from 'react';

/**
 * Home page - house browser listing.
 * Placeholder until house browser component is implemented.
 */
export function HomePage(): ReactNode {
  return (
    <div className="page page--home">
      <h2>Browse Houses</h2>
      <p className="placeholder-text">
        House listings will appear here once the API is connected.
      </p>
      {/* HouseBrowser component will be added in issue #2 */}
    </div>
  );
}
