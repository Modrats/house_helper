import { useState, useEffect } from 'react';
import type { HouseListItem } from '../types';

interface UseHousesResult {
  data: HouseListItem[] | undefined;
  isLoading: boolean;
  error: Error | null;
}

async function fetchHouses(): Promise<HouseListItem[]> {
  const res = await fetch('/api/houses');
  if (!res.ok) throw new Error('Failed to fetch houses');
  return res.json() as Promise<HouseListItem[]>;
}

export function useHouses(): UseHousesResult {
  const [data, setData] = useState<HouseListItem[] | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    fetchHouses()
      .then((result) => {
        if (!cancelled) {
          setData(result);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setIsLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, []);

  return { data, isLoading, error };
}
