import { useState, useEffect } from 'react';
import type { House } from '../types';

interface UseHouseResult {
  data: House | undefined;
  isLoading: boolean;
  error: Error | null;
}

async function fetchHouse(id: string): Promise<House> {
  const res = await fetch(`/api/houses/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch house ${id}`);
  return res.json() as Promise<House>;
}

export function useHouse(houseId: string | undefined): UseHouseResult {
  const [data, setData] = useState<House | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!houseId) {
      setData(undefined);
      setIsLoading(false);
      setError(null);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    fetchHouse(houseId)
      .then((result) => {
        if (!cancelled) { setData(result); setIsLoading(false); }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setIsLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [houseId]);

  return { data, isLoading, error };
}
