import { useState, useCallback, useRef, useEffect, type ReactNode } from 'react';

interface BeforeAfterSliderProps {
  original: string;
  transformed: string;
  label?: string;
}

export function BeforeAfterSlider({
  original,
  transformed,
  label = 'Room',
}: BeforeAfterSliderProps): ReactNode {
  const containerRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState(50); // percent
  const [isDragging, setIsDragging] = useState(false);

  const clamp = (v: number) => Math.max(0, Math.min(100, v));

  const getPositionFromEvent = useCallback((clientX: number): number => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return 50;
    return clamp(((clientX - rect.left) / rect.width) * 100);
  }, []);

  const handleMouseDown = () => setIsDragging(true);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging) return;
      setPosition(getPositionFromEvent(e.clientX));
    },
    [isDragging, getPositionFromEvent]
  );

  const handleMouseUp = useCallback(() => setIsDragging(false), []);

  const handleTouchMove = useCallback(
    (e: TouchEvent) => {
      const touch = e.touches[0];
      if (touch) setPosition(getPositionFromEvent(touch.clientX));
    },
    [getPositionFromEvent]
  );

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Keyboard support on the divider handle
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowLeft') setPosition((p) => clamp(p - 5));
    if (e.key === 'ArrowRight') setPosition((p) => clamp(p + 5));
  };

  return (
    <div
      ref={containerRef}
      className={`before-after-slider${isDragging ? ' before-after-slider--dragging' : ''}`}
      aria-label={`Before and after comparison for ${label}`}
      onTouchMove={(e) => handleTouchMove(e.nativeEvent)}
    >
      {/* Original (before) — always full width underneath */}
      <div className="before-after-slider__before">
        <img
          src={original}
          alt={`${label} — original`}
          className="before-after-slider__image"
          loading="lazy"
          draggable={false}
        />
        <span className="before-after-slider__label before-after-slider__label--before" aria-hidden="true">
          Before
        </span>
      </div>

      {/* Transformed (after) — clipped to show only left portion up to position% */}
      <div
        className="before-after-slider__after"
        style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}
        aria-hidden="true"
      >
        <img
          src={transformed}
          alt={`${label} — imagineered`}
          className="before-after-slider__image"
          loading="lazy"
          draggable={false}
        />
        <span className="before-after-slider__label before-after-slider__label--after">
          After ✨
        </span>
      </div>

      {/* Divider handle */}
      <div
        role="slider"
        aria-label={`Reveal imagineered ${label}`}
        aria-valuenow={Math.round(position)}
        aria-valuemin={0}
        aria-valuemax={100}
        tabIndex={0}
        className="before-after-slider__handle"
        style={{ left: `${position}%` }}
        onMouseDown={handleMouseDown}
        onKeyDown={handleKeyDown}
      >
        <div className="before-after-slider__line" />
        <div className="before-after-slider__grip" aria-hidden="true">⇔</div>
      </div>
    </div>
  );
}
