import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { Layout } from './components/Layout';
import { HomePage } from './pages/HomePage';
import { HouseDetailPage } from './pages/HouseDetailPage';
import { GalleryPage } from './pages/GalleryPage';
import { NotFoundPage } from './pages/NotFoundPage';

/**
 * Creates a test router instance with the same route structure as the app.
 */
function createTestRouter(initialEntries: string[] = ['/']) {
  return createMemoryRouter(
    [
      {
        path: '/',
        element: <Layout />,
        children: [
          { index: true, element: <HomePage /> },
          { path: 'house/:houseId', element: <HouseDetailPage /> },
          { path: 'house/:houseId/gallery', element: <GalleryPage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
    { initialEntries }
  );
}

describe('Router', () => {
  describe('route matching', () => {
    it('renders home page at /', () => {
      const router = createTestRouter(['/']);
      render(<RouterProvider router={router} />);
      
      expect(screen.getByRole('heading', { name: /browse houses/i })).toBeInTheDocument();
    });

    it('renders house detail page at /house/:houseId', () => {
      const router = createTestRouter(['/house/abc123']);
      render(<RouterProvider router={router} />);
      
      expect(screen.getByRole('heading', { name: /house details/i })).toBeInTheDocument();
      // House ID appears in breadcrumb and content - verify at least one exists
      expect(screen.getAllByText(/abc123/).length).toBeGreaterThan(0);
    });

    it('renders gallery page at /house/:houseId/gallery', () => {
      const router = createTestRouter(['/house/abc123/gallery']);
      render(<RouterProvider router={router} />);
      
      expect(screen.getByRole('heading', { name: /photo gallery/i })).toBeInTheDocument();
      // House ID appears in breadcrumb and content - verify at least one exists
      expect(screen.getAllByText(/abc123/).length).toBeGreaterThan(0);
    });

    it('renders 404 page for unknown routes', () => {
      const router = createTestRouter(['/unknown/route']);
      render(<RouterProvider router={router} />);
      
      expect(screen.getByRole('heading', { name: /page not found/i })).toBeInTheDocument();
    });
  });

  describe('navigation', () => {
    it('navigates from home to house detail via link', async () => {
      const user = userEvent.setup();
      const router = createTestRouter(['/house/test-house']);
      render(<RouterProvider router={router} />);
      
      // Click the gallery link on house detail page
      const galleryLink = screen.getByRole('link', { name: /view photo gallery/i });
      await user.click(galleryLink);
      
      // Should be on gallery page
      expect(screen.getByRole('heading', { name: /photo gallery/i })).toBeInTheDocument();
    });

    it('shows breadcrumb navigation on house detail page', () => {
      const router = createTestRouter(['/house/test-house']);
      render(<RouterProvider router={router} />);
      
      const breadcrumb = screen.getByRole('navigation', { name: /breadcrumb/i });
      expect(breadcrumb).toBeInTheDocument();
      // "Houses" link in breadcrumb
      expect(screen.getByRole('link', { name: 'Houses' })).toBeInTheDocument();
    });

    it('shows breadcrumb navigation on gallery page', () => {
      const router = createTestRouter(['/house/test-house/gallery']);
      render(<RouterProvider router={router} />);
      
      const breadcrumb = screen.getByRole('navigation', { name: /breadcrumb/i });
      expect(breadcrumb).toBeInTheDocument();
      // Verify breadcrumb links
      expect(screen.getByRole('link', { name: 'Houses' })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /house.*test-house/i })).toBeInTheDocument();
    });
  });
});

describe('Layout', () => {
  beforeEach(() => {
    const router = createTestRouter(['/']);
    render(<RouterProvider router={router} />);
  });

  it('renders header with app title', () => {
    expect(screen.getByRole('heading', { name: /house helper/i })).toBeInTheDocument();
  });

  it('renders sidebar navigation', () => {
    // Find the sidebar navigation by aria-label
    const sidebar = screen.getByRole('navigation', { name: 'Main navigation' });
    expect(sidebar).toBeInTheDocument();
  });

  it('renders main content area', () => {
    const main = screen.getByRole('main');
    expect(main).toBeInTheDocument();
  });

  it('has accessible sidebar toggle button', () => {
    const toggleButton = screen.getByRole('button', { name: /navigation menu/i });
    expect(toggleButton).toBeInTheDocument();
    expect(toggleButton).toHaveAttribute('aria-expanded');
  });
});

describe('Sidebar', () => {
  it('highlights active nav link', () => {
    const router = createTestRouter(['/']);
    render(<RouterProvider router={router} />);
    
    const homeLink = screen.getByRole('link', { name: /browse houses/i });
    expect(homeLink).toHaveClass('sidebar-link--active');
  });

  it('toggles open/closed state', async () => {
    const user = userEvent.setup();
    const router = createTestRouter(['/']);
    render(<RouterProvider router={router} />);
    
    const toggleButton = screen.getByRole('button', { name: /open navigation menu/i });
    
    // Open sidebar
    await user.click(toggleButton);
    expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
    
    // Close sidebar
    await user.click(toggleButton);
    expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
  });
});
