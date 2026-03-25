/**
 * TypeScript interfaces matching the House Helper backend API responses.
 * Field names use snake_case to match JSON directly — no transform needed.
 * Backend API spec: http://localhost:8000/docs
 */

/** Summary item from GET /api/houses */
export interface HouseListItem {
  slug: string;
  photo_count: number;
  status: string;
  has_filter_results: boolean;
  thumbnail_url: string | null;
}

/** Per-criterion filter results from the text filter stage */
export interface FilterResult {
  p1: Record<string, boolean>;
  p2: Record<string, boolean>;
  excluded: Record<string, boolean>;
  passed: boolean;
}

/** Photo object from GET /api/houses/{slug}/photos */
export interface HousePhoto {
  filename: string;
  url: string;
  room_type: string | null;
  confidence: number | null;
  imagineered_url: string | null;
}

/** Full house detail from GET /api/houses/{slug} */
export interface House {
  slug: string;
  listing_text: string;
  status: string;
  photo_count: number;
  room_count: number;
  filter_results: FilterResult;
  photos: HousePhoto[];
}

/**
 * Room grouping from GET /api/houses/{slug}/rooms.
 * photos contains filenames only — use GET /api/houses/{slug}/photos?room_type=X
 * to get full photo objects with URLs.
 */
export interface RoomClassification {
  room_type: string;
  display_name: string;
  photo_count: number;
  photos: string[];
}
