import type { ReactNode } from 'react';
import type { RoomClassification } from '../types';

interface RoomSidebarProps {
  rooms: RoomClassification[];
  selectedRoomType: string | null;
  onSelectRoom: (roomType: string) => void;
  isLoading?: boolean;
}

function RoomSidebarSkeleton(): ReactNode {
  return (
    <nav className="room-sidebar room-sidebar--loading" aria-label="Room types">
      <h3 className="room-sidebar__title">Rooms</h3>
      <ul className="room-sidebar__list" role="list">
        {Array.from({ length: 6 }).map((_, i) => (
          <li key={i} className="room-sidebar__item room-sidebar__item--skeleton">
            <span className="room-sidebar__skeleton-label" />
            <span className="room-sidebar__skeleton-badge" />
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function RoomSidebar({
  rooms,
  selectedRoomType,
  onSelectRoom,
  isLoading = false,
}: RoomSidebarProps): ReactNode {
  if (isLoading) {
    return <RoomSidebarSkeleton />;
  }

  return (
    <nav className="room-sidebar" aria-label="Room types">
      <h3 className="room-sidebar__title">Rooms</h3>
      <ul className="room-sidebar__list" role="list">
        {rooms.map((room) => {
          const isActive = room.roomType === selectedRoomType;
          return (
            <li key={room.roomType} className="room-sidebar__item">
              <button
                type="button"
                className={`room-sidebar__button${isActive ? ' room-sidebar__button--active' : ''}`}
                onClick={() => onSelectRoom(room.roomType)}
                aria-current={isActive ? 'true' : undefined}
              >
                <span className="room-sidebar__room-name">
                  {room.hasImaginedVersion && (
                    <span className="room-sidebar__sparkle" aria-label="Has imagineered version">
                      ✨{' '}
                    </span>
                  )}
                  {room.displayName}
                </span>
                <span className="room-sidebar__badge" aria-label={`${room.photoCount} photos`}>
                  {room.photoCount}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
