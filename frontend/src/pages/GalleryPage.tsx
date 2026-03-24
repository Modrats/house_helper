import type { ReactNode } from 'react';
import { useParams, Link } from 'react-router-dom';

/**
 * Gallery page showing house photos with before/after comparison.
 * Placeholder until gallery component is implemented.
 */
export function GalleryPage(): ReactNode {
  const { houseId } = useParams<{ houseId: string }>();

  if (!houseId) {
    return (
      <div className="page page--error">
        <h2>Gallery not found</h2>
        <p>No house ID provided.</p>
        <Link to="/">Return to browse</Link>
      </div>
    );
  }

  return (
    <div className="page page--gallery">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/">Houses</Link>
        <span aria-hidden="true"> / </span>
        <Link to={`/house/${houseId}`}>House {houseId}</Link>
        <span aria-hidden="true"> / </span>
        <span aria-current="page">Gallery</span>
      </nav>

      <h2>Photo Gallery</h2>
      <p className="placeholder-text">
        Photo gallery for house <code>{houseId}</code> will appear here.
        This will include the before/after image slider for imagineered rooms.
      </p>

      {/* GalleryViewer and BeforeAfterSlider components will be added in issues #4 and #5 */}
    </div>
  );
}
