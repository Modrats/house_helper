import { useState, type ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useHouses } from '../hooks/useHouses';
import type { HouseListItem } from '../types';

function HouseBrowserSkeleton(): ReactNode {
  return (
    <nav className="house-browser" aria-label="House list">
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

function formatAddress(house: HouseListItem): string {
  const { street, houseNumber, city } = house.address;
  return `${street} ${houseNumber}, ${city}`;
}

interface HouseBrowserSidebarProps {
  className?: string;
}

export function HouseBrowserSidebar({ className = '' }: HouseBrowserSidebarProps): ReactNode {
  const navigate = useNavigate();
  const { houseId: activeHouseId } = useParams<{ houseId: string }>();
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
    formatAddress(h).toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <nav className={`house-browser ${className}`} aria-label="House list">
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
            const isActive = house.id === activeHouseId;
            return (
              <li key={house.id} className="house-item">
                <button
                  type="button"
                  className={`house-item__button${isActive ? ' house-item__button--active' : ''}`}
                  onClick={() => navigate(`/house/${house.id}`)}
                  aria-current={isActive ? 'page' : undefined}
                >
                  {formatAddress(house)}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </nav>
  );
}
