import type { ReactNode } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useHouse } from '../hooks/useHouse';

function formatPrice(price: number): string {
  return new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(price);
}

function formatAddress(house: { address: { street: string; houseNumber: string; city: string; postalCode: string } }): string {
  const { street, houseNumber, city, postalCode } = house.address;
  return `${street} ${houseNumber}, ${postalCode} ${city}`;
}

export function HouseDetailPage(): ReactNode {
  const { houseId } = useParams<{ houseId: string }>();
  const { data: house, isLoading, error } = useHouse(houseId);

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
        <span aria-current="page">{house ? formatAddress(house) : `House ${houseId}`}</span>
      </nav>

      {isLoading && (
        <div className="house-detail house-detail--loading">
          <div className="house-detail__screenshot-skeleton" aria-busy="true" />
          <div className="house-detail__meta-skeleton" />
        </div>
      )}

      {error && (
        <div className="house-detail__error" role="alert">
          <h2>Could not load house</h2>
          <p>{error.message}</p>
          <Link to="/">Return to browse</Link>
        </div>
      )}

      {house && (
        <article className="house-detail">
          {/* Screenshot */}
          <div className="house-detail__screenshot">
            <img
              src={`/outputs/houses/${houseId}/screenshot.png`}
              alt={`Screenshot of ${formatAddress(house)}`}
              className="house-detail__screenshot-img"
              loading="lazy"
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
            />
          </div>

          {/* Header */}
          <header className="house-detail__header">
            <h2 className="house-detail__address">{formatAddress(house)}</h2>
            <p className="house-detail__price">{formatPrice(house.listing.price)}</p>
          </header>

          {/* Listing summary */}
          <dl className="house-detail__stats">
            <div className="house-detail__stat">
              <dt>Living area</dt>
              <dd>{house.listing.livingArea} m²</dd>
            </div>
            <div className="house-detail__stat">
              <dt>Bedrooms</dt>
              <dd>{house.listing.bedrooms}</dd>
            </div>
            {house.listing.plotSize && (
              <div className="house-detail__stat">
                <dt>Plot size</dt>
                <dd>{house.listing.plotSize} m²</dd>
              </div>
            )}
            {house.listing.yearBuilt && (
              <div className="house-detail__stat">
                <dt>Year built</dt>
                <dd>{house.listing.yearBuilt}</dd>
              </div>
            )}
            {house.listing.energyLabel && (
              <div className="house-detail__stat">
                <dt>Energy label</dt>
                <dd className={`energy-label energy-label--${house.listing.energyLabel.toLowerCase()}`}>
                  {house.listing.energyLabel}
                </dd>
              </div>
            )}
          </dl>

          {/* Description */}
          {house.description && (
            <section className="house-detail__description">
              <h3>About this house</h3>
              <p>{house.description}</p>
            </section>
          )}

          {/* Actions */}
          <div className="house-detail__actions">
            <Link
              to={`/house/${houseId}/gallery`}
              className="button button--primary"
            >
              View Photo Gallery →
            </Link>
            {house.sourceUrl && (
              <a
                href={house.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="button button--secondary"
              >
                View original listing ↗
              </a>
            )}
          </div>
        </article>
      )}
    </div>
  );
}

