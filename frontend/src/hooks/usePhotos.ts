import { useState, useEffect } from 'react';
import type { HousePhoto } from '../types';
import { api } from '../services/api';

interface UsePhotosResult {
  data: HousePhoto[] | undefined;
  isLoading: boolean;
  error: Error | null;
}

export function usePhotos(houseId: string | undefined): UsePhotosResult {
  const [data, setData] = useState<HousePhoto[] | undefined>(undefined);
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

    api.getPhotos(houseId)
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
  }, [houseId]);

  return { data, isLoading, error };
}
