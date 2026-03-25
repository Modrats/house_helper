import { useState, type ReactNode } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useRoomClassifications } from '../hooks/useRoomClassifications';
import { usePhotos } from '../hooks/usePhotos';
import { RoomSidebar } from '../components/RoomSidebar';
import { PhotoGrid } from '../components/PhotoGrid';
import { BeforeAfterSlider } from '../components/BeforeAfterSlider';

// CSS custom property for transitions
const galleryStyle = {
  '--transition-fast': '0.15s ease',
} as React.CSSProperties;

export function GalleryPage(): ReactNode {
  const { houseId } = useParams<{ houseId: string }>();
  const [selectedRoomType, setSelectedRoomType] = useState<string | null>(null);

  const { data: rooms, isLoading: roomsLoading } = useRoomClassifications(houseId);

  const roomList = rooms ?? [];
  const effectiveRoomType = selectedRoomType ?? roomList[0]?.room_type ?? null;

  const { data: photos, isLoading: photosLoading } = usePhotos(houseId, effectiveRoomType);
  const selectedRoom = roomList.find((r) => r.room_type === effectiveRoomType) ?? null;

  // Find a photo that has an imagineered version for the before/after slider
  const sliderPhoto = (photos ?? []).find((p) => p.imagineered_url != null);

  if (!houseId) {
    return (
      <div className="page page--error">
        <h2>Gallery not found</h2>
        <p>No house ID provided.</p>
        <Link to="/">Return to browse</Link>
      </div>
    );
  }

  return (
    <div className="page page--gallery" style={galleryStyle}>
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/">Houses</Link>
        <span aria-hidden="true"> / </span>
        <Link to={`/house/${houseId}`}>House {houseId}</Link>
        <span aria-hidden="true"> / </span>
        <span aria-current="page">Gallery</span>
      </nav>

      <h2>Photo Gallery</h2>

      <div className="gallery-layout">
        <div className="gallery-layout__sidebar">
          <RoomSidebar
            rooms={roomList}
            selectedRoomType={effectiveRoomType}
            onSelectRoom={setSelectedRoomType}
            isLoading={roomsLoading}
          />
        </div>

        <main className="gallery-layout__main" aria-label="Photo grid">
          {sliderPhoto?.imagineered_url && (
            <BeforeAfterSlider
              original={sliderPhoto.url}
              transformed={sliderPhoto.imagineered_url}
              label={selectedRoom?.display_name ?? 'Room'}
            />
          )}
          <PhotoGrid
            photos={photos ?? []}
            roomName={selectedRoom?.display_name ?? 'Room'}
            isLoading={photosLoading}
          />
        </main>
      </div>
    </div>
  );
}
