/**
 * Typed API client for the House Helper backend.
 * Uses native fetch — no external HTTP libraries.
 */

import type { HouseListItem, House, RoomClassification, HousePhoto } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** List all houses */
  getHouses(): Promise<HouseListItem[]> {
    return get<HouseListItem[]>('/api/houses');
  },

  /** Get full house details */
  getHouse(id: string): Promise<House> {
    return get<House>(`/api/houses/${id}`);
  },

  /** Get room classifications for a house */
  getRoomClassifications(houseId: string): Promise<RoomClassification[]> {
    return get<RoomClassification[]>(`/api/houses/${houseId}/room-classifications`);
  },

  /** Get photos for a house, optionally filtered by room type */
  getPhotos(houseId: string, roomType?: string): Promise<HousePhoto[]> {
    const path = roomType
      ? `/api/houses/${houseId}/photos?roomType=${encodeURIComponent(roomType)}`
      : `/api/houses/${houseId}/photos`;
    return get<HousePhoto[]>(path);
  },
};
