import { useEffect, useRef, type ReactNode } from 'react';
import type { HousePhoto } from '../types';

interface PhotoLightboxProps {
  photos: HousePhoto[];
  currentIndex: number;
  onClose: () => void;
  onPrev: () => void;
  onNext: () => void;
}

export function PhotoLightbox({
  photos,
  currentIndex,
  onClose,
  onPrev,
  onNext,
}: PhotoLightboxProps): ReactNode {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const photo = photos[currentIndex];

  // Focus close button on open
  useEffect(() => {
    closeButtonRef.current?.focus();
  }, []);

  // Keyboard navigation + focus trap
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key === 'ArrowLeft') {
        onPrev();
        return;
      }
      if (e.key === 'ArrowRight') {
        onNext();
        return;
      }
      // Focus trap: Tab stays within dialog
      if (e.key === 'Tab') {
        const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
          'button, [href], input, [tabindex]:not([tabindex="-1"])'
        );
        if (!focusable || focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose, onPrev, onNext]);

  if (!photo) return null;

  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < photos.length - 1;

  return (
    <div
      className="lightbox"
      role="dialog"
      aria-modal="true"
      aria-label="Photo viewer"
      ref={dialogRef}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <button
        ref={closeButtonRef}
        className="lightbox__close"
        type="button"
        onClick={onClose}
        aria-label="Close photo viewer"
      >
        ✕
      </button>

      <div className="lightbox__content">
        {hasPrev && (
          <button
            className="lightbox__nav lightbox__nav--prev"
            type="button"
            onClick={onPrev}
            aria-label="Previous photo"
          >
            ‹
          </button>
        )}

        <figure className="lightbox__figure">
          <img
            className="lightbox__image"
            src={photo.url}
            alt={photo.caption ?? 'Room photo'}
          />
          {photo.caption && (
            <figcaption className="lightbox__caption">{photo.caption}</figcaption>
          )}
        </figure>

        {hasNext && (
          <button
            className="lightbox__nav lightbox__nav--next"
            type="button"
            onClick={onNext}
            aria-label="Next photo"
          >
            ›
          </button>
        )}
      </div>

      <div className="lightbox__counter" aria-live="polite">
        {currentIndex + 1} / {photos.length}
      </div>
    </div>
  );
}
