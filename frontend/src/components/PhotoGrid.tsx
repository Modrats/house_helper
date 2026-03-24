import { useState, type ReactNode } from 'react';
import type { HousePhoto } from '../types';
import { PhotoLightbox } from './PhotoLightbox';

interface PhotoGridProps {
  photos: HousePhoto[];
  roomName: string;
  isLoading?: boolean;
}

function PhotoGridSkeleton(): ReactNode {
  return (
    <div className="photo-grid photo-grid--loading" aria-busy="true" aria-label="Loading photos">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="photo-card photo-card--skeleton" />
      ))}
    </div>
  );
}

export function PhotoGrid({ photos, roomName, isLoading = false }: PhotoGridProps): ReactNode {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  if (isLoading) {
    return <PhotoGridSkeleton />;
  }

  if (photos.length === 0) {
    return (
      <div className="photo-grid photo-grid--empty">
        <p>No photos available for this room.</p>
      </div>
    );
  }

  const openLightbox = (index: number) => setLightboxIndex(index);
  const closeLightbox = () => setLightboxIndex(null);
  const prevPhoto = () =>
    setLightboxIndex((i) => (i !== null && i > 0 ? i - 1 : i));
  const nextPhoto = () =>
    setLightboxIndex((i) => (i !== null && i < photos.length - 1 ? i + 1 : i));

  return (
    <>
      <div
        className="photo-grid"
        role="list"
        aria-label={`${roomName} photos`}
      >
        {photos.map((photo, index) => (
          <div key={photo.id} className="photo-card" role="listitem">
            <button
              type="button"
              className="photo-card__button"
              onClick={() => openLightbox(index)}
              aria-label={photo.caption ?? `${roomName} photo ${index + 1}`}
            >
              <img
                className="photo-card__image"
                src={photo.url}
                srcSet={`${photo.url}?w=200 200w, ${photo.url}?w=400 400w`}
                sizes="(max-width: 600px) 200px, 400px"
                alt={photo.caption ?? `${roomName} photo ${index + 1}`}
                loading="lazy"
              />
              {photo.isImaginedVersion && (
                <span className="photo-card__badge" aria-label="Imagineered version">
                  ✨ Imagineered
                </span>
              )}
            </button>
          </div>
        ))}
      </div>

      {lightboxIndex !== null && (
        <PhotoLightbox
          photos={photos}
          currentIndex={lightboxIndex}
          onClose={closeLightbox}
          onPrev={prevPhoto}
          onNext={nextPhoto}
        />
      )}
    </>
  );
}
