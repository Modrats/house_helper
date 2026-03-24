import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

/**
 * Sidebar navigation component.
 * Collapsible on mobile via isOpen prop.
 */
export function Sidebar({ isOpen, onToggle }: SidebarProps): ReactNode {
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div 
          className="sidebar-overlay"
          onClick={onToggle}
          aria-hidden="true"
        />
      )}
      
      <aside className={`sidebar ${isOpen ? 'sidebar--open' : ''}`}>
        <nav className="sidebar-nav" aria-label="Main navigation">
          <NavLink 
            to="/" 
            className={({ isActive }) => 
              `sidebar-link ${isActive ? 'sidebar-link--active' : ''}`
            }
            onClick={() => isOpen && onToggle()}
          >
            <span className="sidebar-link-icon" aria-hidden="true">🏠</span>
            <span className="sidebar-link-text">Browse Houses</span>
          </NavLink>
          
          {/* Placeholder for future navigation items */}
          {/* 
          <NavLink to="/favorites" className="sidebar-link">
            <span className="sidebar-link-icon">⭐</span>
            <span className="sidebar-link-text">Favorites</span>
          </NavLink>
          <NavLink to="/criteria" className="sidebar-link">
            <span className="sidebar-link-icon">🎯</span>
            <span className="sidebar-link-text">My Criteria</span>
          </NavLink>
          */}
        </nav>
      </aside>
    </>
  );
}
