import { useState, type ReactNode } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { ErrorBoundary } from './ErrorBoundary';

/**
 * Main app layout with persistent sidebar and content area.
 * Responsive: sidebar collapses to hamburger menu on mobile.
 */
export function Layout(): ReactNode {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = () => setSidebarOpen((prev) => !prev);

  return (
    <div className="app-layout">
      {/* Header */}
      <header className="app-header">
        <button
          className="sidebar-toggle"
          onClick={toggleSidebar}
          aria-label={sidebarOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={sidebarOpen}
        >
          <span className="sidebar-toggle-icon" aria-hidden="true">
            {sidebarOpen ? '✕' : '☰'}
          </span>
        </button>
        <h1 className="app-title">House Helper</h1>
      </header>

      <div className="app-body">
        {/* Sidebar */}
        <Sidebar isOpen={sidebarOpen} onToggle={toggleSidebar} />

        {/* Main content */}
        <main className="app-main" id="main-content">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
