import type { ReactNode } from 'react';
import { useParams, Link } from 'react-router-dom';

/**
 * House detail page showing full house information.
 * Placeholder until detail component is implemented.
 */
export function HouseDetailPage(): ReactNode {
  const { houseId } = useParams<{ houseId: string }>();

  if (!houseId) {
    return (
      <div className="page page--error">
        <h2>House not found</h2>
        <p>No house ID provided.</p>
        <Link to="/">Return to browse</Link>
      </div>
    );
  }

  return (
    <div className="page page--house-detail">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/">Houses</Link>
        <span aria-hidden="true"> / </span>
        <span aria-current="page">House {houseId}</span>
      </nav>

      <h2>House Details</h2>
      <p className="placeholder-text">
        Details for house <code>{houseId}</code> will appear here once the API is connected.
      </p>
      
      <Link to={`/house/${houseId}/gallery`} className="gallery-link">
        View Photo Gallery →
      </Link>

      {/* HouseDetail component will be added in issue #3 */}
    </div>
  );
}
