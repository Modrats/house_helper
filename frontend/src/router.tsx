import { createBrowserRouter, type RouteObject } from 'react-router-dom';
import { Layout } from './components/Layout';
import { HomePage } from './pages/HomePage';
import { HouseDetailPage } from './pages/HouseDetailPage';
import { GalleryPage } from './pages/GalleryPage';
import { NotFoundPage } from './pages/NotFoundPage';

/**
 * Application route configuration.
 * 
 * Routes:
 * - /                      Home page with house browser
 * - /house/:houseId        House detail page
 * - /house/:houseId/gallery Photo gallery with before/after slider
 * - *                      404 Not Found
 */
const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: 'house/:houseId',
        element: <HouseDetailPage />,
      },
      {
        path: 'house/:houseId/gallery',
        element: <GalleryPage />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
];

export const router = createBrowserRouter(routes);
