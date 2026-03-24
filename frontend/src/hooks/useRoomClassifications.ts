import { useState, useEffect } from 'react';
import type { RoomClassification } from '../types';

interface UseRoomClassificationsResult {
  data: RoomClassification[] | undefined;
  isLoading: boolean;
  error: Error | null;
}

async function fetchRoomClassifications(houseId: string): Promise<RoomClassification[]> {
  const res = await fetch(`/api/houses/${houseId}/room-classifications`);
  if (!res.ok) throw new Error('Failed to fetch room classifications');
  return res.json() as Promise<RoomClassification[]>;
}

export function useRoomClassifications(houseId: string | undefined): UseRoomClassificationsResult {
  const [data, setData] = useState<RoomClassification[] | undefined>(undefined);
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

    fetchRoomClassifications(houseId)
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

    return () => {
      cancelled = true;
    };
  }, [houseId]);

  return { data, isLoading, error };
}
