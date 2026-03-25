import type { ReactNode } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useHouse } from '../hooks/useHouse';
import type { FilterResult } from '../types/house';

function formatSlug(slug: string): string {
  return slug.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function CriteriaPanel({ results }: { results: FilterResult }): ReactNode {
  const allP1 = Object.entries(results.p1);
  const allP2 = Object.entries(results.p2);
  const allExcluded = Object.entries(results.excluded);

  return (
    <section className="house-detail__criteria">
      <h3>
        Filter result:{' '}
        <span className={results.passed ? 'criteria-pass' : 'criteria-fail'}>
          {results.passed ? '✓ Passed' : '✗ Failed'}
        </span>
      </h3>
      {allP1.length > 0 && (
        <div className="criteria-group">
          <h4>Must-have</h4>
          <ul className="criteria-list">
            {allP1.map(([k, v]) => (
              <li key={k} className={v ? 'criteria-item--pass' : 'criteria-item--fail'}>
                {v ? '✓' : '✗'} {k}
              </li>
            ))}
          </ul>
        </div>
      )}
      {allP2.length > 0 && (
        <div className="criteria-group">
          <h4>Nice-to-have</h4>
          <ul className="criteria-list">
            {allP2.map(([k, v]) => (
              <li key={k} className={v ? 'criteria-item--pass' : 'criteria-item--neutral'}>
                {v ? '✓' : '·'} {k}
              </li>
            ))}
          </ul>
        </div>
      )}
      {allExcluded.length > 0 && (
        <div className="criteria-group">
          <h4>Dealbreakers</h4>
          <ul className="criteria-list">
            {allExcluded.map(([k, v]) => (
              <li key={k} className={v ? 'criteria-item--fail' : 'criteria-item--pass'}>
                {v ? '✗' : '✓'} {k}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
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
        <span aria-current="page">{house ? formatSlug(house.slug) : houseId}</span>
      </nav>

      <h2>{house ? formatSlug(house.slug) : 'House Details'}</h2>

      <div className="house-detail__actions">
        <Link to={`/house/${houseId}/gallery`} className="button button--primary">
          View Photo Gallery
        </Link>
      </div>

      {isLoading && (
        <div className="house-detail house-detail--loading">
          <div className="house-detail__screenshot-skeleton" aria-busy="true" />
          <div className="house-detail__meta-skeleton" />
        </div>
      )}

      {error && (
        <div className="house-detail__error" role="alert">
          <p>{error.message}</p>
          <Link to="/">Return to browse</Link>
        </div>
      )}

      {house && (
        <article className="house-detail">
          <dl className="house-detail__stats">
            <div className="house-detail__stat">
              <dt>Status</dt>
              <dd>{house.status}</dd>
            </div>
            <div className="house-detail__stat">
              <dt>Photos</dt>
              <dd>{house.photo_count}</dd>
            </div>
            <div className="house-detail__stat">
              <dt>Rooms</dt>
              <dd>{house.room_count}</dd>
            </div>
          </dl>

          <CriteriaPanel results={house.filter_results} />

          <section className="house-detail__description">
            <h3>Listing</h3>
            <pre className="house-detail__listing-text">{house.listing_text}</pre>
          </section>
        </article>
      )}
    </div>
  );
}

