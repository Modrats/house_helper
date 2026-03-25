import { useState, type ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useHouses } from '../hooks/useHouses';
import type { HouseListItem } from '../types';

function HouseBrowserSkeleton(): ReactNode {
  return (
    <nav className="house-browser" aria-label="House list">
      <h2 className="house-browser__title">Browse Houses</h2>
      <div className="house-browser__search house-browser__search--skeleton" />
      <ul className="house-browser__list" role="list">
        {Array.from({ length: 5 }).map((_, i) => (
          <li key={i} className="house-item house-item--skeleton">
            <span className="house-item__skeleton-name" />
          </li>
        ))}
      </ul>
    </nav>
  );
}

function formatSlug(slug: string): string {
  return slug.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function statusBadge(house: HouseListItem): string {
  return house.status === 'filtered' && house.has_filter_results ? ' ✓' : '';
}

interface HouseBrowserSidebarProps {
  className?: string;
}

export function HouseBrowserSidebar({ className = '' }: HouseBrowserSidebarProps): ReactNode {
  const navigate = useNavigate();
  const { houseId: activeSlug } = useParams<{ houseId: string }>();
  const { data: houses, isLoading, error } = useHouses();
  const [filter, setFilter] = useState('');

  if (isLoading) return <HouseBrowserSkeleton />;

  if (error) {
    return (
      <nav className="house-browser" aria-label="House list">
        <p className="house-browser__error" role="alert">
          Could not load houses.
        </p>
      </nav>
    );
  }

  const filtered = (houses ?? []).filter((h) =>
    h.slug.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <nav className={`house-browser ${className}`} aria-label="House list">
      <h2 className="house-browser__title">Browse Houses</h2>
      <div className="house-browser__search-wrapper">
        <label className="visually-hidden" htmlFor="house-filter">
          Filter houses
        </label>
        <input
          id="house-filter"
          type="search"
          className="house-browser__search"
          placeholder="Filter houses…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      {filtered.length === 0 ? (
        <p className="house-browser__empty">No houses match your filter.</p>
      ) : (
        <ul className="house-browser__list" role="list">
          {filtered.map((house) => {
            const isActive = house.slug === activeSlug;
            return (
              <li key={house.slug} className="house-item">
                <button
                  type="button"
                  className={`house-item__button${isActive ? ' house-item__button--active' : ''}`}
                  onClick={() => navigate(`/house/${house.slug}`)}
                  aria-current={isActive ? 'page' : undefined}
                >
                  {formatSlug(house.slug)}{statusBadge(house)}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </nav>
  );
}
