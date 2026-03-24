"""Concrete implementations of pipeline interfaces."""

from .local_storage import LocalStorage
from .room_classifier import RoomClassifier

__all__ = ["LocalStorage", "RoomClassifier"]
