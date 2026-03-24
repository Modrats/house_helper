"""IDataSource abstract base class — generic storage CRUD.

Provides a storage-backend-agnostic interface for reading and writing
data. Does not know about domain concepts like houses or rooms.

Domain-specific logic belongs in HouseRepository, which wraps IDataSource
and translates between generic path operations and house-domain queries.

Example implementations:
    - LocalStorage: Reads/writes on the local filesystem.
    - AzureStorageService: Reads/writes from Azure Blob + Table Storage.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class IDataSource(ABC):
    """Generic CRUD interface for the storage backend.

    All methods operate on opaque paths/keys interpreted by the
    implementation. LocalStorage treats them as filesystem paths;
    cloud implementations map them to blob paths or table keys.

    This interface intentionally has no knowledge of houses, rooms,
    or pipeline structure — it is pure storage plumbing.
    """

    @abstractmethod
    def read_json(self, path: str | Path) -> dict:
        """Read and parse a JSON file from storage.

        Args:
            path: Storage path or key.

        Returns:
            Parsed JSON as a dict.

        Raises:
            FileNotFoundError: If the path does not exist.
        """

    @abstractmethod
    def write_json(self, path: str | Path, data: dict) -> None:
        """Write a dict as JSON to storage.

        Parent directories (or equivalent) are created automatically.

        Args:
            path: Storage path or key.
            data: Data to serialise and write.
        """

    @abstractmethod
    def list_keys(self, prefix: str | Path) -> list[str]:
        """List keys (paths) directly under a given prefix.

        Args:
            prefix: Directory or key prefix to list.

        Returns:
            Sorted list of key strings under the prefix.
            Empty list if the prefix does not exist.
        """

    @abstractmethod
    def read_bytes(self, path: str | Path) -> bytes:
        """Read raw bytes from storage.

        Args:
            path: Storage path or key.

        Returns:
            Raw bytes content.

        Raises:
            FileNotFoundError: If the path does not exist.
        """

    @abstractmethod
    def exists(self, path: str | Path) -> bool:
        """Check whether a path/key exists in storage.

        Args:
            path: Storage path or key.

        Returns:
            True if the path exists, False otherwise.
        """
