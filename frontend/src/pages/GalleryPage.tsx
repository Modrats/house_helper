import { useState, type ReactNode } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useRoomClassifications } from '../hooks/useRoomClassifications';
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

  const { data: rooms, isLoading } = useRoomClassifications(houseId);

  if (!houseId) {
    return (
      <div className="page page--error">
        <h2>Gallery not found</h2>
        <p>No house ID provided.</p>
        <Link to="/">Return to browse</Link>
      </div>
    );
  }

  const roomList = rooms ?? [];
  const selectedRoom = roomList.find((r) => r.roomType === selectedRoomType) ?? roomList[0] ?? null;
  const effectiveRoomType = selectedRoom?.roomType ?? null;

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
            isLoading={isLoading}
          />
        </div>

        <main className="gallery-layout__main" aria-label="Photo grid">
          {selectedRoom?.hasImaginedVersion && selectedRoom.photos.length > 0 && (() => {
            const original = selectedRoom.photos.find((p) => !p.isImaginedVersion);
            const transformed = selectedRoom.photos.find((p) => p.isImaginedVersion);
            if (original && transformed) {
              return (
                <BeforeAfterSlider
                  original={original.url}
                  transformed={transformed.url}
                  label={selectedRoom.displayName}
                />
              );
            }
            return null;
          })()}
          <PhotoGrid
            photos={selectedRoom?.photos ?? []}
            roomName={selectedRoom?.displayName ?? 'Room'}
            isLoading={isLoading}
          />
        </main>
      </div>
    </div>
  );
}
