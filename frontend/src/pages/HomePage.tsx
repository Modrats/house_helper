import type { ReactNode } from 'react';
import { HouseBrowserSidebar } from '../components/HouseBrowserSidebar';

export function HomePage(): ReactNode {
  return (
    <div className="page page--home">
      <HouseBrowserSidebar />
    </div>
  );
}
