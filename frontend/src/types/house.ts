/**
 * TypeScript interfaces for house data types.
 * These will be replaced by auto-generated types from the OpenAPI spec
 * once the backend API is ready.
 */

export interface HousePhoto {
  id: string;
  url: string;
  roomType?: string;
  caption?: string;
  isImaginedVersion?: boolean;
  originalPhotoId?: string;
}

export interface HouseRoom {
  id: string;
  name: string;
  type: string;
  photos: HousePhoto[];
}

export interface HouseAddress {
  street: string;
  houseNumber: string;
  city: string;
  postalCode: string;
  neighborhood?: string;
}

export interface HouseListingDetails {
  price: number;
  pricePerSqm?: number;
  livingArea: number;
  plotSize?: number;
  bedrooms: number;
  bathrooms?: number;
  yearBuilt?: number;
  energyLabel?: string;
}

export interface House {
  id: string;
  address: HouseAddress;
  listing: HouseListingDetails;
  description?: string;
  rooms: HouseRoom[];
  photos: HousePhoto[];
  sourceUrl?: string;
  createdAt: string;
  updatedAt: string;
}

export interface HouseListItem {
  id: string;
  address: HouseAddress;
  listing: Pick<HouseListingDetails, 'price' | 'livingArea' | 'bedrooms'>;
  thumbnailUrl?: string;
}
