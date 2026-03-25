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
  getHouse(slug: string): Promise<House> {
    return get<House>(`/api/houses/${slug}`);
  },

  /** Get room classifications for a house */
  getRoomClassifications(slug: string): Promise<RoomClassification[]> {
    return get<RoomClassification[]>(`/api/houses/${slug}/rooms`);
  },

  /** Get photos for a house, optionally filtered by room type */
  getPhotos(slug: string, roomType?: string | null): Promise<HousePhoto[]> {
    const path = roomType
      ? `/api/houses/${slug}/photos?room_type=${encodeURIComponent(roomType)}`
      : `/api/houses/${slug}/photos`;
    return get<HousePhoto[]>(path);
  },
};
