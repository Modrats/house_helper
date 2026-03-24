"""Local filesystem implementation of IDataSource.

Reads and writes files on the local filesystem. This implementation has
no knowledge of houses, rooms, or pipeline structure — all domain-specific
path construction and business logic belongs in HouseRepository.

All methods accept absolute paths and operate directly on the filesystem.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..interfaces.data_source import IDataSource


class LocalStorage(IDataSource):
    """Filesystem-backed storage — reads and writes at absolute paths.

    Stateless: no directories are configured at construction time.
    The caller (HouseRepository) is responsible for constructing
    the correct absolute paths to pass to each method.
    """

    def read_json(self, path: str | Path) -> dict:
        """Read and parse a JSON file."""
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def write_json(self, path: str | Path, data: dict) -> None:
        """Write a dict as JSON, creating parent directories as needed."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def list_keys(self, prefix: str | Path) -> list[str]:
        """List entries directly under the given directory, sorted."""
        p = Path(prefix)
        if not p.exists():
            return []
        return sorted(str(child) for child in p.iterdir())

    def read_bytes(self, path: str | Path) -> bytes:
        """Read raw bytes from a file."""
        return Path(path).read_bytes()

    def exists(self, path: str | Path) -> bool:
        """Return True if the path exists on the filesystem."""
        return Path(path).exists()
